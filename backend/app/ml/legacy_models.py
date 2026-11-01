"""Legacy checkpoint architectures; no model downloads."""
import torch
import torch.nn as nn

class CNNBaseline(nn.Module):
    """
    Lightweight 4-block 2D Convolutional Baseline for Mel-Spectrogram classification.
    Input shape: (batch, 1, 128, T)
    Output shape: (batch, 2) -> [logit_real, logit_fake]
    """

    def __init__(self, num_classes: int = 2, dropout: float = 0.3):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            # Block 2
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            # Block 3
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            # Block 4
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4)),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        logits = self.classifier(feat)
        return logits



def build_legacy_model(name):
    name = name.lower().strip()
    if name in {"cnn", "baseline", "cnn_baseline"}:
        return CNNBaseline()
    if "lcnn" in name:
        from app.ml.architectures.lcnn import LCNNAudioDetector
        return LCNNAudioDetector(num_classes=2)
    if name in {"resnet18", "resnet-18", "resnet", "resnet18_spectrogram"}:
        from torchvision.models import resnet18
        net = resnet18(weights=None)
        net.conv1 = nn.Conv2d(1, 64, 7, stride=2, padding=3, bias=False)
        net.fc = nn.Linear(net.fc.in_features, 2)
        return net
    raise ValueError(f"Unsupported checkpoint architecture: {name}")
