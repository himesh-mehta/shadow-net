"""
Neural Network Architectures for SHADOW-NET Deepfake Voice Detection.
Includes:
1. CNNBaseline: Lightweight 4-stage convolutional neural network.
2. ResNet18AudioClassifier: Adapted torchvision ResNet-18 for 1-channel spectrograms,
   matching backend/app/ml/classifier.py state_dict keys exactly.
"""

import torch
import torch.nn as nn
import torchvision.models as models


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


def build_resnet18(pretrained: bool = False, num_classes: int = 2) -> nn.Module:
    """
    Builds adapted ResNet-18 for 1-channel audio spectrograms.
    Exact match to backend/app/ml/classifier.py architecture.
    """
    weights = models.ResNet18_Weights.DEFAULT if pretrained else None
    net = models.resnet18(weights=weights)

    # Adapt first conv: change in_channels from 3 to 1
    orig_conv = net.conv1
    net.conv1 = nn.Conv2d(
        in_channels=1,
        out_channels=orig_conv.out_channels,
        kernel_size=orig_conv.kernel_size,
        stride=orig_conv.stride,
        padding=orig_conv.padding,
        bias=False,
    )

    if pretrained:
        # Average pretrained RGB channels across the single grayscale channel
        with torch.no_grad():
            net.conv1.weight.copy_(orig_conv.weight.mean(dim=1, keepdim=True))

    # Adapt final fully-connected layer
    net.fc = nn.Linear(net.fc.in_features, num_classes)

    return net


def get_model(model_name: str, pretrained: bool = False) -> nn.Module:
    """
    Factory function for training models.
    """
    name = model_name.lower().strip()
    if name in ["resnet18", "resnet-18", "resnet"]:
        return build_resnet18(pretrained=pretrained)
    elif name in ["cnn", "baseline", "cnn_baseline"]:
        return CNNBaseline()
    else:
        raise ValueError(f"Unknown model name '{model_name}'. Choose 'resnet18' or 'cnn'.")
