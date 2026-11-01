"""A worsening final epoch must not replace the best checkpoint."""
import json
import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from training import train
from training.dataset import AudioSpoofDataset


def test_best_and_last_checkpoints_are_separate(tmp_path, monkeypatch):
    class Dataset(torch.utils.data.Dataset):
        def __init__(self, *args): pass
        def __len__(self): return 2
        def __getitem__(self, i): return torch.zeros(1, 128, 63), i
    for name in ['train.json', 'val.json']:
        (tmp_path / name).write_text('[]')
    monkeypatch.setattr(train, 'AudioSpoofDataset', Dataset)
    monkeypatch.setattr(train, 'get_model', lambda *args, **kwargs: torch.nn.Linear(1, 2))
    def metrics(auc):
        return dict(accuracy=0.5, f1=0.5, roc_auc=auc, fpr=0.5)
    monkeypatch.setattr(train, 'train_epoch', lambda *args: (0.5, metrics(0.5)))
    scores = iter([(0.1, metrics(0.95)), (0.9, metrics(0.6))])
    monkeypatch.setattr(train, 'evaluate', lambda *args: next(scores))
    output = tmp_path / 'best.pth'
    result = train.train_pipeline(data_dir=str(tmp_path), epochs=2, output_model=str(output), device_name='cpu')
    assert torch.load(output, weights_only=True)['epoch'] == 1
    assert torch.load(tmp_path / 'best.last.pth', weights_only=True)['epoch'] == 2
    assert result['best_epoch'] == 1


def test_bad_training_audio_is_not_a_labeled_zero_tensor(tmp_path):
    manifest = tmp_path / 'train.json'
    manifest.write_text(json.dumps([{'audio_path':str(tmp_path / 'missing.wav'), 'label':1}]))
    dataset = AudioSpoofDataset(str(manifest))
    with pytest.raises(RuntimeError, match='Cannot load dataset audio'):
        dataset[0]
