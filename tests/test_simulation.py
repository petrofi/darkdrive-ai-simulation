import sys
import os
import unittest
import torch

# Proje ana dizinini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.steering_model import SteeringModel

class TestSteeringModel(unittest.TestCase):
    def setUp(self):
        self.model = SteeringModel()

    def test_forward_pass_shape(self):
        # Batch: 4, Channels: 3, Height: 160, Width: 320 (Klasik donkeycar/udacity boyutu)
        dummy_input = torch.rand(4, 3, 160, 320)
        output = self.model(dummy_input)
        
        # Çıktı her resim için tek bir steering açısı olmalı (Batch size, 1)
        self.assertEqual(output.shape, (4, 1))

    def test_forward_values_range(self):
        # Girdilerin normalize edildiğini ve modelin hata vermeden çıktı ürettiğini doğrula
        dummy_input = torch.ones(1, 3, 160, 320)
        output = self.model(dummy_input)
        self.assertFalse(torch.isnan(output).any(), "Model çıktısında NaN değerler var!")

if __name__ == '__main__':
    unittest.main()
