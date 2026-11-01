# Editorial review

Written for the author before publication. Nothing has been published, committed or pushed.

## 1. Where the system differs from the brief

The brief assumed some things the code does not do. The articles describe the code, and two of them change what the title promises. Please check you are comfortable with these.

| Brief expected | What the code does | Effect |
| --- | --- | --- |
| A tool-using shopping agent | Moks is a fixed three-node pipeline. The model chooses nothing | A4 opens by saying so. The walkthrough shows input → retrieval → model → validation, because a model-driven tool invocation does not exist |
| Cart updates and checkout in the agent | Moks has neither | A4 lists them as not implemented |
| A "decision loop" | No loop exists | The file keeps the requested name; the caption says there is no loop |
| An AI gateway integrating model providers | The gateway never calls a model. It stores config and admits requests | A2 says so in its first paragraph |
| Response streaming | None, anywhere | A2 has a short section saying so |
| Agent reaching services through MCP | Moks does not use MCP; nothing in the cluster does | A3 states it early |

**Keep the title of A4?** "How the RoboShop AI Shopping Agent Works" matches the repository and the search term, while the article argues Moks is not an agent in the tool-using sense. I think this is honest because the first paragraph settles it, but it is your decision.

## 2. Findings that may be bugs

Found by reading code. None was changed. Each should be confirmed on a running system.

1. **Chat rate limit may be global.** `TRUST_PROXY=true`, but `TRUSTED_PROXY_CIDRS` is set nowhere, so `client_address` always returns the direct peer. For chat that is the Moks pod, so 10 chats a minute may be shared by every shopper on a replica, and 300 a minute by everyone behind `web`. Sidecars may also change the peer address. The same variable is read in `user-service/registration.py`. `tests/load/VERIFICATION.md` records hitting a rate limit at accelerated pacing, which fits but does not prove this. A2 publishes this with a warning. Fix it first or keep the warning.
2. **`mcp-server` has no inbound AuthorizationPolicy.** Harmless today because policies are in dry-run. When `allow-nothing` is enforced, in-cluster MCP clients will be denied. The effect on `kubectl port-forward` is not verified.
3. **NetworkPolicy enforcement is unconfirmed.** The `mcp-server-clients` policy exists and `aws-eks-nodeagent` runs, but I did not confirm that network policy is enabled on the VPC CNI. A3 says only that the policy "admits" labelled pods.
4. **Empty-evidence questions still pay for a model call.** This looks intended so the model can suggest a refinement, but an off-topic prompt costs a generation.
5. **A failed history save discards a paid answer.** `ChatHistory.save` raises 503 after generation.
6. **Moks prose can claim a cart action.** Only the instruction prevents "Done, it's in your cart". A4 says so.
7. **Three retrieval implementations disagree.** Moks, `ai-gateway/lib/catalogue.py` and catalogue-service.
8. **Site editor bug, unrelated to RoboShop.** In `src/lib/editor/markdown.ts`, a paragraph starting with "No. " is parsed as an ordered list and turns into "1. " on save. `npm test` caught it in a draft of A1. I reworded the two sentences and did not change the editor. Any post with such a paragraph would be altered by the visual editor.

## 3. Verification limitations

**Diagram exports.** The `.drawio` files are real and editable, but **the SVG and PNG files are not draw.io exports.** I tried to download the official draw.io desktop build to a scratch folder, and this session's permission policy refused it because it runs externally downloaded code. I did not work around that. Instead, `build_diagrams.py` writes the `.drawio` XML and the SVG from one layout model, and `render_png.sh` screenshots the SVGs with your installed Chrome.

- XML validated with `xmllint`, and checked by `verify_series.py`.
- SVG and PNG inspected by eye.
- **Not done:** opening the `.drawio` files in draw.io. Text wrapping, edge label positions and fonts may differ slightly from the SVG, so please open each file once.
- To get true exports, install draw.io desktop and run `draw.io -x -f svg -p <page> -o <out> <file>` for each page, or allow the download and ask me to run it.

**Test runs.** Python 3.11 with pinned requirements in a scratch environment. The Dockerfiles use Python 3.14, which was not available.

| Suite | Result |
| --- | --- |
| `services/moks/tests` | 65 passed |
| `services/mcp-server/tests` | 20 passed |
| `services/mcp-server/demo/demo.py` | Ran as documented |
| `services/ai-gateway/tests` | 41 run, 34 passed, 7 errors. 6 are a `mongomock` duplicate-key error in the `test_admin_console` fixture. 1 needs `httpx`. Both look like test-environment issues, but I did not resolve them |
| `tests/python` | `test_readiness`: 4 of 5 passed, 1 error. `test_llm`, `test_failover`: not run, because `boto3` was not in that environment |
| Node, Java and Go suites | Not run |

**Site checks**, with Node 26, after the final edits:

| Check | Result |
| --- | --- |
| `npm test` | 399 passed, including content validation, internal links and the editor round trip |
| `npm run lint`, `npm run typecheck` | Pass |
| `APP_ENV=production npm run build` | Pass |
| Preview render of all four drafts | 200, one H1, every image has alt text, no errors logged. The embedded database was pointed at a scratch folder because the default `.data/pglite` path failed here |
| `verify_series.py` | Pass: 13 code excerpts match their source files, plus links, images, SEO lengths, XML, secret and stock-phrase scans |
| Phone width | Figures checked at 342 px wide. A screenshot of the full article page came back blank in headless Chrome, so the article layout itself was **not** checked on a phone |

**Not verified at all:**

- No real model was called. No provider adapter was exercised against Bedrock or Ollama.
- The conversation table in A4 used a stub model on real retrieval code, and says so.
- No failure injection on EKS. The failure table in A1 comes from code, except the Moks row.
- No latency or cost measurement exists. The articles quote none.
- MCP was probed locally against the synthetic fixture, never the deployed pod.
- Live checks are a snapshot from 2026-11-01.

## 4. Decisions needed

1. **Overlap with live posts.** A1 targets the same readers as `/blog/roboshop-ai-microservices`, and the content audit already plans a merge there. A1 is framed around the AI boundary and links to it, but you may want to choose one primary page for "RoboShop AI architecture". Publishing A1 alongside the existing post without a decision risks them competing.
2. **Live publishing path.** Live posts are in PostgreSQL. These are new slugs, so the per-file import can create them as drafts. Follow section 6 of `docs/CONTENT_AUDIT.md`, resolve and delete each `<Todo>`, and deploy first so the new images exist.
3. **Moks on EKS.** Three drafts state it is absent. Deploying it would change A1, A2, A3 and A4 in several places, and let the stub be replaced.
4. **Rate-limit finding.** Publish, or fix first.
5. **Licence.** `LICENSE` is proprietary, yet the articles quote short excerpts from your public repository. Confirm you are happy with that, and with readers treating the design as a pattern only.
6. **Twenty robots or 32.** README and the existing site article say twenty. The live API returns 32.
7. **A public statement about a security gap.** A3 explains that the session design does not meet the MCP authorization profile, and that `update_cart` has no confirmation. This is accurate and the server is private, but it is your call whether to publish it now or after a fix.

## 5. Author voice

- The body uses first-person singular because the repository and site show one author. The brief says "we", so change it if you prefer. The MOKS article has the same issue.
- I did not invent motives, lessons or incidents. Reasons come from code comments and READMEs. "I built this as a personal project to explore..." in A1 is my inference from the site's description, so **please confirm or rewrite it.**
- Places where your own reasons would add value: why Moks was deliberately kept read-only, why keyword retrieval was preferred, why the MCP server was built before it had a client, and why Moks is not on EKS.
- Check the FAQ answers in A3 and A4. "The repository does not record that decision" could be replaced with your real reason.
- Confirm any AI-assistance disclosure against the site's AI use policy. No claim is made about how the text was written.

## 6. Structured data

The site generates JSON-LD itself (`src/lib/seo/jsonld.ts`), so nothing needs adding to the articles.

- `contentType: tutorial` is used, which renders as `BlogPosting` and keeps these out of the news sitemap. This avoids the `analysis` to `NewsArticle` problem noted in the content audit. It may mean the site labels them "Tutorial".
- The site has no `TechArticle` type. If you want one, it is a code change. Example with unknowns marked:

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Building an MCP Server for RoboShop AI",
  "description": "A code-level MCP server walkthrough: roles, transports, tool schemas, session forwarding, trust boundaries and the risks that remain in RoboShop AI.",
  "url": "https://jithendar.com/blog/roboshop-ai-mcp-server",
  "author": {
    "@type": "Person",
    "name": "Jithendar Dharmapuri",
    "url": "https://jithendar.com/authors/jithendar-dharmapuri"
  },
  "datePublished": "[PLACEHOLDER: set at publication]",
  "dateModified": "[PLACEHOLDER: set at publication]",
  "image": "[PLACEHOLDER: no cover image exists yet]",
  "publisher": "[PLACEHOLDER: publication name is unconfirmed]"
}
```

The author's `jobTitle` is unset in `content/authors/jithendar-dharmapuri.mdx`, and the content audit notes a conflict in how it is displayed, so none is used.

## 7. Before publishing

- [ ] Open each `.drawio` file in draw.io
- [ ] Add cover images. None was created. `featuredImage` must be raster, so SVG figures cannot be used
- [ ] Re-run the live checks in `evidence-map.md`
- [ ] Replace the stub trace if Moks gets a real provider
- [ ] Resolve and delete every `<Todo>`
- [ ] Set `publishedAt` at publication
