import wave
import math
import struct

sample_rate = 16000
duration = 3
freq = 440
amplitude = 0.3

samples = []
for i in range(int(sample_rate * duration)):
    sample = amplitude * math.sin(2 * math.pi * freq * i / sample_rate)
    samples.append(int(sample * 32767))

with wave.open('sample_audio.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(struct.pack('<' + 'h' * len(samples), *samples))

print('Created sample_audio.wav')
