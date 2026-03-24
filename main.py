from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
import torch
import soundfile as sf
import numpy as np
from huggingface_hub import hf_hub_download

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

inputs = processor(text="Hello world", return_tensors="pt")
input_ids = inputs["input_ids"]

speaker_embedding_path = hf_hub_download(
    repo_id="Matthijs/cmu-arctic-xvectors",
    filename="speaker_embeddings/cmu_us_bdl_arctic-wav-arctic_a0009.npy",
    repo_type="dataset",
)
speaker_embeddings = torch.tensor(np.load(speaker_embedding_path)).unsqueeze(0)

speech = model.generate_speech(input_ids, speaker_embeddings, vocoder=vocoder)

sf.write("output.wav", speech.numpy(), samplerate=16000)
print("Audio gespeichert als output.wav")
