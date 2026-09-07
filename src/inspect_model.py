import onnxruntime as ort
from pathlib import Path

MODEL_PATH = Path("models/aasist-l.onnx")

print("=" * 50)
print("AASIST-L ONNX MODEL INSPECTION")
print("=" * 50)

# Load model
session = ort.InferenceSession(
    str(MODEL_PATH),
    providers=["CPUExecutionProvider"]
)

print("\nModel loaded successfully!")

# Runtime providers
print("\nAvailable providers:")
for provider in ort.get_available_providers():
    print(f"  - {provider}")

# Inputs
print("\nINPUTS:")
for i, inp in enumerate(session.get_inputs()):
    print(f"\nInput {i + 1}:")
    print(f"  Name : {inp.name}")
    print(f"  Shape: {inp.shape}")
    print(f"  Type : {inp.type}")

# Outputs
print("\nOUTPUTS:")
for i, out in enumerate(session.get_outputs()):
    print(f"\nOutput {i + 1}:")
    print(f"  Name : {out.name}")
    print(f"  Shape: {out.shape}")
    print(f"  Type : {out.type}")

print("\n" + "=" * 50)
print("Inspection complete")
print("=" * 50)