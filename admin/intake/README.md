# The intake: the comms vault, its lanes, and the drain

Ported from [riskmandate.ai's intake](https://github.com/Risk-Mandate/riskmandate.ai/tree/dev/scripts/intake)
(branch `dev`, 30 September 2026), following
[the handover brief](https://riskmandate.ai/admin/briefs/handover__the-contact-form-for-another-site/),
[Agent Contact v0.1](https://sgit.ai/docs/agent-contact.html) and
[the append-lanes API](https://sgit.ai/api/append-lanes.html).

The diniscruz.ai agent has one identity, `agent@diniscruz.ai`, published in
`.well-known/sgit-agents.json` and on `/agents/`. Its inbox is a pair of append lanes on a private
comms vault (the id is in the contact file) on `dev.send.sgraph.ai`:

| lane | who writes | what |
|---|---|---|
| `agents` | agents on the allow list, signed with their published key | `agent-message/v1` |
| `site` | the contact form on the site, encrypted in the visitor's browser, unsigned | `X-DC-Form: contact` |

Both tokens are public (the protocol's design and the owner's decision of 29 September 2026).
**The vault's own key is the one secret.** It is given to a session as `COMMS_KEY` in the
environment and is never in a file in this repository or in the vault. Everything else that
opens the vault is derived from it in memory, each session:

- the write key: `sgit vault derive-keys "$COMMS_KEY"`
- the listing key: `HMAC-SHA256(write_key, "agent-contact/enum-key/v1")`
- the key-store secret: `HMAC-SHA256(write_key, "agent-contact/key-pass/agent/v1")`, which `sgit pki`
  reads from `SG_SEND_PASSPHRASE`

The identity's private keys are in the vault at `agent-contact/keys/store/<fingerprint>/`, encrypted
under the key-store secret, so a holder of the vault's read key cannot use them.

## A drain, per session

```bash
cd "$SCRATCH" && sgit clone "$COMMS_KEY" comms-diniscruz-ai      # or sgit pull in an existing clone
COMMS_KEY="$COMMS_KEY" node "$REPO/admin/intake/drain.mjs" --vault comms-diniscruz-ai --dry-run   # look first
COMMS_KEY="$COMMS_KEY" node "$REPO/admin/intake/drain.mjs" --vault comms-diniscruz-ai             # then file
cd comms-diniscruz-ai && sgit commit -m "drain: <n> accepted, <m> quarantined" && sgit push --token "$SGSEND_TOKEN"
```

What arrives under `agent-contact/accepted/` is a `.eml` and its `.enc`, one pair per message. The
`.eml` is what a person reads. `agent-contact/log.jsonl` has one line per file: lane, result,
subject, and the reply-to address a form gave. A contact message is answered by email from
`agent@diniscruz.ai`.

The drain never pushes, never deletes on the host, and never writes a key anywhere. Files it cannot
open or does not trust go to `quarantine/` with the reason in the log. They are still marked
processed on the host, so a bad file cannot block the lane.

## The lanes themselves

`configure.mjs` (re)registers the lanes and can purge processed files. It needs the vault key and
the SG/Send account credential as `SGSEND_TOKEN`, because `configure` and `purge` are the owner's
calls. `configure` replaces the anchor list, so it always sends both lanes. To revoke a token: mint
a new one, update `lanes.json` in the clone and the contact file on the site, run `configure.mjs`,
then release the site.

```bash
COMMS_KEY=… SGSEND_TOKEN=… node admin/intake/configure.mjs --vault comms-diniscruz-ai            # from lanes.json + the contact file
COMMS_KEY=… SGSEND_TOKEN=… node admin/intake/configure.mjs --vault comms-diniscruz-ai --purge    # drop processed files on the host
```

`configure` answers 404 on a vault that has never been pushed (learned on riskmandate.ai, 30
September), so the vault's first commit is pushed before any lane is configured.

## The browser side

`contact.html` inlines two scripts from riskmandate.ai's `site/contact.html`. The first is
`SgEnvelope`, as is: sgit's hybrid envelope v2 built with Web Crypto (AES-256-GCM, RSA-OAEP
SHA-256, `{v,w,i,c}` base64, the `.enc` text base64'd once more for the lane). The second is the
form logic, with this site's addresses and `X-DC-*` headers. The page fetches the contact file at
submit time, checks the key against its fingerprint, encrypts, and POSTs to `append/write`. If
anything fails, the same text becomes a mailto to `agent@diniscruz.ai`.

## The checks

`node --test admin/build/test_agents.mjs` recomputes the fingerprints from the PEMs, checks the
tokens are lane-shaped, refuses anything private in the contact file, and checks `/agents/` shows
the published fingerprints. CI runs it on every push.
