import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from assistant.persona_engine import PersonaEngine
from assistant.llm_client import LLMClient

class TestLLMIntegration(unittest.TestCase):
    @patch('assistant.llm_client.AutoModelForCausalLM')
    @patch('huggingface_hub.hf_hub_download')
    def test_llm_client_initialization(self, mock_download, mock_automodel):
        # Mock download to avoid actual network call
        mock_download.return_value = "/tmp/fake_model.gguf"
        
        # Mock model
        mock_model_instance = MagicMock()
        mock_automodel.from_pretrained.return_value = mock_model_instance
        
        # We need to ensure the import works for the patch to take effect on the right object
        # but since it is a local import, patching the source module 'huggingface_hub.hf_hub_download' is safer.
        
        client = LLMClient()
        
        # Check if it tried to download (since we didn't provide path and it likely doesn't exist)
        # Note: In our code, we check os.path.exists first. 
        # To test download logic, we'd need to mock os.path.exists too, but let's assume 
        # the default path doesn't exist in this test environment.
        
        self.assertIsNotNone(client.model)
        mock_automodel.from_pretrained.assert_called()

    @patch('assistant.persona_engine.LLMClient')
    def test_persona_engine_intent(self, MockLLMClient):
        # Setup mock client
        mock_client = MockLLMClient.return_value
        mock_client.model = True # pretend loaded
        mock_client.generate.return_value = "Index: 1" # simulate LLM picking index 1
        
        engine = PersonaEngine()
        
        intents = [
            {'name': 'weather', 'keywords': ['rain']},
            {'name': 'lights', 'keywords': ['on', 'off']}
        ]
        
        chosen, score = engine.parse_intent("Turn on the lights", intents)
        
        self.assertEqual(chosen['name'], 'lights')
        self.assertEqual(score, 1.0)
        
        # Verify prompt structure (roughly)
        args, _ = mock_client.generate.call_args
        prompt = args[0]
        self.assertIn("Turn on the lights", prompt)
        self.assertIn("weather", prompt)

    @patch('assistant.persona_engine.LLMClient')
    def test_persona_engine_decorate(self, MockLLMClient):
        mock_client = MockLLMClient.return_value
        mock_client.model = True
        mock_client.generate.return_value = "It is sunny in London."
        
        engine = PersonaEngine()
        response = engine.decorate("What's the weather?", {'city': 'London', 'forecast': 'sunny'})
        
        self.assertEqual(response, "It is sunny in London.")

if __name__ == '__main__':
    unittest.main()
