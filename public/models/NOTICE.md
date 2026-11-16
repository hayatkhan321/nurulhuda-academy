# tajweed-v2-int8.onnx

A browser-friendly build of the HisnLabs **tajweed-v2** model (https://huggingface.co/Hisnlabs/tajweed-v2,
Apache License 2.0, © HISNLABS CYBER AI FZCO; see `nurulhuda/vendor/hisnlabs/LICENSE`).

Changed by Nurul Huda Academy on 17 November 2026: re-quantized from the published `onnx/model-fp32.onnx`
(sha256 44851c4d…684d) with onnxruntime `quantize_dynamic(op_types_to_quantize=["MatMul"], QInt8)`, so the two
convolution layers stay in float. The published int8 file uses ConvInteger, which onnxruntime-web cannot run.
Accuracy on obadx/qdat_bench (159 recordings) is the same as the published int8 file (phoneme error 8–9 % for adults).
