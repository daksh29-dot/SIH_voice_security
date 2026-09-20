import numpy as np
import onnxruntime as ort


class W2V2AASISTSpoofDetector:
    """
    ONNX Runtime wrapper for the official W2V2-AASIST model.

    Input:
        Raw mono 16 kHz audio
        Exactly 64,600 samples per model inference

    Output:
        Spoof probability in the range [0, 1]
        Higher value = more likely spoof
    """

    WINDOW_SAMPLES = 64600

    def __init__(self, model_path):
        self.model_path = str(model_path)

        self.session = ort.InferenceSession(
            self.model_path,
            providers=["CPUExecutionProvider"]
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        print("[+] W2V2-AASIST ONNX loaded successfully")
        print(f"    Input : {self.input_name}")
        print(f"    Output: {self.output_name}")

    def predict_segment(self, waveform):
        """
        Run one 64,600-sample audio segment through W2V2-AASIST.

        Returns:
            float: spoof probability
        """

        waveform = np.asarray(waveform, dtype=np.float32).flatten()

        # Short audio → zero-pad (not tile-repeat; see segment_audio.py for rationale)
        if len(waveform) < self.WINDOW_SAMPLES:
            padded = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
            padded[:len(waveform)] = waveform
            waveform = padded

        # Long audio -> use only the first model window here.
        # Long-audio handling will be done by segment_audio.py.
        elif len(waveform) > self.WINDOW_SAMPLES:
            waveform = waveform[:self.WINDOW_SAMPLES]

        # ONNX expects [batch, 64600]
        input_tensor = waveform[np.newaxis, :].astype(np.float32)

        outputs = self.session.run(
            [self.output_name],
            {self.input_name: input_tensor}
        )

        logits = outputs[0]

        # Convert logits -> probabilities
        logits = logits.astype(np.float64)

        logits = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probabilities = exp_logits / np.sum(
            exp_logits,
            axis=1,
            keepdims=True
        )

        # W2V2-AASIST:
        # class 0 = spoof
        # class 1 = bona fide
        spoof_probability = float(probabilities[0, 0])

        return spoof_probability