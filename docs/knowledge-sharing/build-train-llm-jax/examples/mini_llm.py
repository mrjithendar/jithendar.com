# mini_llm.py: a learning example that runs on a laptop CPU in seconds.
# Not a production trainer: no Flax, no data loader, no sharding, toy data.
import jax
import jax.numpy as jnp
import optax
import orbax.checkpoint as ocp
from pathlib import Path

# 1-2. Data and a character-level tokenizer (id 0 = padding)
corpus = ["the cat sat on the mat", "the dog ran to the cat", "a cat and a dog sat"]
chars = sorted(set("".join(corpus)))
stoi = {c: i + 1 for i, c in enumerate(chars)}
itos = {i: c for c, i in stoi.items()}
vocab_size, max_len = len(stoi) + 1, 24

# 3. Padded batch + mask: fixed shape (3, 24) every step
def encode(s):
    ids = [stoi[c] for c in s][:max_len]
    return ids + [0] * (max_len - len(ids))
batch = jnp.array([encode(s) for s in corpus])
inputs, targets = batch[:, :-1], batch[:, 1:]          # predict the next character
loss_mask = targets != 0                                 # don't learn to predict padding

# 4. Parameters: token + positional embeddings, one attention block, output head
d_model, n_heads = 32, 4
def init_params(key):
    ks = jax.random.split(key, 8)
    n = lambda k, shape: jax.random.normal(k, shape) * 0.02
    return {
        "tok_emb": n(ks[0], (vocab_size, d_model)),
        "pos_emb": n(ks[1], (max_len, d_model)),
        "wq": n(ks[2], (d_model, d_model)), "wk": n(ks[3], (d_model, d_model)),
        "wv": n(ks[4], (d_model, d_model)), "wo": n(ks[5], (d_model, d_model)),
        "w_ff": n(ks[6], (d_model, 4 * d_model)), "w_out_ff": n(ks[7], (4 * d_model, d_model)),
    }

def layer_norm(x, eps=1e-5):
    mean, var = x.mean(-1, keepdims=True), x.var(-1, keepdims=True)
    return (x - mean) / jnp.sqrt(var + eps)

# 5. One Transformer block: causal multi-head self-attention + MLP, with residuals
def forward(params, ids):
    B, T = ids.shape
    x = params["tok_emb"][ids] + params["pos_emb"][jnp.arange(T)]
    h = layer_norm(x)
    split = lambda t: t.reshape(B, T, n_heads, -1).transpose(0, 2, 1, 3)   # (B, H, T, d)
    q, k, v = (split(h @ params[w]) for w in ("wq", "wk", "wv"))
    scores = q @ k.transpose(0, 1, 3, 2) / jnp.sqrt(q.shape[-1])
    causal = jnp.tril(jnp.ones((T, T), dtype=bool))
    pad = (ids != 0)[:, None, None, :]                 # don't attend to padding keys
    scores = jnp.where(causal & pad, scores, -1e9)
    attn = jax.nn.softmax(scores, axis=-1) @ v
    x = x + attn.transpose(0, 2, 1, 3).reshape(B, T, d_model) @ params["wo"]
    x = x + jax.nn.gelu(layer_norm(x) @ params["w_ff"]) @ params["w_out_ff"]
    return layer_norm(x) @ params["tok_emb"].T          # logits, tied to the embeddings

# 6. Loss: cross-entropy on real (non-pad) target tokens only
def loss_fn(params, inputs, targets, mask):
    logits = forward(params, inputs)
    losses = optax.softmax_cross_entropy_with_integer_labels(logits, targets)
    return (losses * mask).sum() / mask.sum()

# 7-9. Gradients with value_and_grad, AdamW from Optax, whole step under jit
optimizer = optax.adamw(learning_rate=3e-3)

@jax.jit
def train_step(params, opt_state, inputs, targets, mask):
    loss, grads = jax.value_and_grad(loss_fn)(params, inputs, targets, mask)
    updates, opt_state = optimizer.update(grads, opt_state, params)
    return optax.apply_updates(params, updates), opt_state, loss

params = init_params(jax.random.key(0))
opt_state = optimizer.init(params)
for step in range(301):
    params, opt_state, loss = train_step(params, opt_state, inputs, targets, loss_mask)
    if step % 100 == 0:
        print(f"step {step:3d}  loss {loss:.3f}")

# 10. Save, then restore into the same structure
mngr = ocp.CheckpointManager(Path("/tmp/mini-llm-ckpt").resolve(),
                             options=ocp.CheckpointManagerOptions(max_to_keep=2))
mngr.save(step, args=ocp.args.StandardSave({"params": params, "opt_state": opt_state}))
mngr.wait_until_finished()
abstract = jax.tree_util.tree_map(ocp.utils.to_shape_dtype_struct,
                                  {"params": params, "opt_state": opt_state})
restored = mngr.restore(mngr.latest_step(), args=ocp.args.StandardRestore(abstract))
print("restored loss:", float(loss_fn(restored["params"], inputs, targets, loss_mask)))

# Bonus: greedy generation from the trained toy model
ids = [stoi[c] for c in "the c"]
for _ in range(12):
    padded = jnp.array([ids + [0] * (max_len - 1 - len(ids))])
    next_id = int(forward(restored["params"], padded)[0, len(ids) - 1].argmax())
    ids.append(next_id)
print("".join(itos.get(i, "?") for i in ids))
