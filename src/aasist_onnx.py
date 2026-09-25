"""Legacy interface using the same strict ONNX contract as the main pipeline.

predict_segment takes one already-preprocessed model window and returns an
uncalibrated score, not a measured probability. Use VoiceSpoofDetector for
quality checks and decisions. No separate, contradictory model defaults.
"""
from config import DEFAULTS, MODEL_PATH
from model import W2V2AASISTSpoofDetector


class AasistOnnxModel(W2V2AASISTSpoofDetector):
    def __init__(self, model_path=MODEL_PATH, settings=DEFAULTS, providers=None):
        super().__init__(model_path, settings, providers)
        self._input_meta = self.session.get_inputs()[0]
        self._output_meta = next(o for o in self.session.get_outputs()
                                 if o.name == self.output_name)

    def input_info(self):
        m = self._input_meta
        return {"name": m.name, "shape": m.shape, "type": m.type}

    def output_info(self):
        m = self._output_meta
        return {"name": m.name, "shape": m.shape, "type": m.type}


if __name__ == "__main__":
    model = AasistOnnxModel()
    print("Input info:", model.input_info())
    print("Output info:", model.output_info())
