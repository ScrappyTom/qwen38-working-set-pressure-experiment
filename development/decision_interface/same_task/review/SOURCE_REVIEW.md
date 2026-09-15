# Pinned runtime source and native boundary evidence

Runtime revision: `7e4c0a96880dae4fc4268ad441f8a6446bd5460a` (b10434).
The live server and native library hashes match the project's pinned runtime.
The upstream source copies in `runtime-source/` were obtained after run closure;
their retrieval is read-only diagnosis, not a runtime replacement. The upstream
MIT license is preserved there. `runtime-source/INDEX.json` records source URLs,
bytes and fingerprints.

The relevant source path is:

1. [server-common.cpp](https://github.com/ggml-org/llama.cpp/blob/7e4c0a96880dae4fc4268ad441f8a6446bd5460a/tools/server/server-common.cpp#L1139)
   accepts either the request's user grammar or response schema. It passes them
   separately to template processing (1243–1248). It assigns template-derived
   grammar/lazy/trigger values (1313–1325), then copies remaining request fields
   (1361 onward). Request fields that already have a derived value do not overwrite it.
2. [chat.cpp](https://github.com/ggml-org/llama.cpp/blob/7e4c0a96880dae4fc4268ad441f8a6446bd5460a/common/chat.cpp#L1117)
   contains the specialized Qwen parser selected by the template's tool markers
   (3364–3369). The pinned template markers are read directly from the same model in
   `template-identification.json`, with no inference. The Qwen route includes
   reasoning before schema-based response content (1187–1195), but generates a
   grammar only for schemas or tools (1153–1156, 1264–1286). Neither is supplied by
   this explicit-grammar request. The user's final-only grammar therefore lacks that
   envelope and reaches sampling as the explicit grammar. The generic autoparser
   has a similar distinction, but it is not the selected Qwen route here.
3. [sampling.cpp](https://github.com/ggml-org/llama.cpp/blob/7e4c0a96880dae4fc4268ad441f8a6446bd5460a/common/sampling.cpp#L264)
   selects eager sampling when the derived lazy flag is false. User grammars are
   not prefilled with template tokens (294–297). With uncapped reasoning and no
   lazy/control policy, the reasoning-budget sampler is not created (310–320).
   `grammar_should_apply` therefore applies the grammar immediately (451–464).

The local request's new grammar root accepts final JSON or a literal-source header.
The native prompt instead ends with an open thinking block. The source chain
explains why those otherwise valid components conflict. The observed endpoint
places all generated text in reasoning because no close delimiter was emitted.

The [native diagnostic script](probe_channel_boundary.py) loads vocabulary only
from the same model and invokes the pinned grammar sampler. It performs no model
decode, context allocation, task operation or completion call. Special-token
recognition is enabled when tokenizing the thinking delimiter. It reproduces six
expected masks, including rejection of token 248069 (`</think>`) before and after
the observed JSON, and acceptance of the JSON plus EOS. Results and input strings
are sealed in `channel-boundary-001/`.

This combination of actual wire/native/output inspection, exact-version code and
native masks supports the host diagnosis. It does not qualify a replacement
constraint. In particular, adding `grammar_lazy` to an API request is not by itself
a demonstrated remedy: server conversion may assign that property first. Any
correction must preserve reasoning/final separation through the actual endpoint.
