<!-- generated from building/index.html by admin/build/build.py — do not edit by hand -->

*[diniscruz.ai](/index.md) · site v0.1.0 · canonical: https://diniscruz.ai/building/index.html*

> The companies Dinis Cruz has founded (sgit.ai, sgraph.ai, MyFeeds.ai, The Cyber Boardroom, RiskMandate.ai, VoiceDebrief.ai), the open-source projects under them (OSBot, MGraph-DB, memory_fs, Issues-FS, sgit-ai), and the sgit.ai network of focused sites.

---

# What I am building

Six companies, one strategy: **everything they ship is open source, and so are their investor materials.** Technology is not the moat. What gets sold is trust, meaning the running, maintained and certified service and the people accountable for it. The reasoning is set out at [open-source.sgit.ai](https://open-source.sgit.ai/).

## Companies

### [sgit.ai](https://sgit.ai)

*Now · Apache-2.0*

Git for encrypted vaults. A vault is a unit of work (data, app, history and sources) versioned like git and handed over with a single read key. No account, no hosting, nothing for the reader to install. The server stores ciphertext it cannot read. `pip install sgit-ai`.

### [sgraph.ai](https://sgraph.ai)

*Commercial home*

SG/Send, the secure file-sharing service built on the sgit layer, and hosted SG/Vaults. The code stays Apache-2.0. What is sold is the running service.

### [MyFeeds.ai](https://investor.myfeeds.ai/)

*Semantic graphs*

Role-aware cybersecurity briefings on semantic knowledge graphs. It is 100% open source and serverless, with no vendor lock-in, and the seed pitch is published in the open.

### [The Cyber Boardroom](https://thecyberboardroom.com)

*Security & the board*

An AI-powered platform that bridges security teams and the board with knowledge-graph technology. The UK company behind sgit.ai and RiskMandate.ai.

### [RiskMandate.ai](https://riskmandate.ai)

*Autonomous systems*

The business risk layer for autonomous systems. There is no "deny" button for a risk, only a decision on how long to accept it and who underwrites it.

### [VoiceDebrief.ai](https://voicedebrief.ai)

*In the browser*

Voice recordings into transcripts and debriefs, entirely client-side. It asks for keys at run time and stores nothing.

## Open source

The code under those companies is Apache-2.0 and published on PyPI. It descends from the OWASP O2 Platform and has been built up one reusable layer at a time.

| Project | What it is |
|---|---|
| **[sgit-ai](https://github.com/SGit-AI/SGit-AI__CLI)** | The sgit CLI: git semantics over client-side AES-256-GCM encrypted vaults. [PyPI](https://pypi.org/project/sgit-ai/). |
| **[OSBot family](https://github.com/owasp-sbot)** | The `osbot-*` libraries: a serverless Python framework for building AI applications, and the building blocks behind the startups. They are published under the owasp-sbot organisation. |
| **MGraph-DB** | A memory-first graph database for GenAI and serverless workloads, publicly credited to the OWASP community. It is the engine behind much of the [graphs research](../research/graphs.md). |
| **memory_fs** | A file-system abstraction used to build file-based representations of documents and standards. For example, [the GDPR as files](../2025/07/02/using-memory_fs-to-build-a-file-based-representation-of-the-gdpr-standard.md). |
| **Issues-FS** | Part of the same Apache-2.0 family on PyPI, alongside memory_fs. |
| **OWASP O2 Platform** | Where it started: the open-source static-analysis engine of 2010 to 2012. [O2 Platform's MethodStreams (2010) →](../2025/02/11/o2-platforms-methodstreams-2010-open-source-sast-engine.md) |

## The sgit.ai network

The [sgit.ai network](https://sgit.ai/network/index.html) is a set of focused sites on `*.sgit.ai`, each taking one question further than an essay can. They share a design language (this site uses it too), and each publishes its argument **before** the thing it describes exists, so the commitments can be checked afterwards. A few that pick up threads from the writing here:

### [graphs.sgit.ai](https://graphs.sgit.ai)

*Graphs*

A node is just a node, and meaning lives in the edges. A grammar for semantic graphs, from five rules to a full position.

### [threat-modeling.sgit.ai](https://threat-modeling.sgit.ai)

*AppSec*

A threat model is a claim you can check. White papers, a threat model validated against the code, and the method behind them.

### [standards.sgit.ai](https://standards.sgit.ai)

*Compliance*

Laws and standards as addressable graphs: the EU AI Act, GDPR, ISO/IEC 27001 and ISO 31000, with a subset method for agents.

### [risks.sgit.ai](https://risks.sgit.ai)

*Risk*

You cannot deny a risk. You can only say how long you accept it, and a named human underwrites it.

### [nhi.sgit.ai](https://nhi.sgit.ai)

*Agents*

Identity for AI agents, and why the industry only answers half the question.

### [open-source.sgit.ai](https://open-source.sgit.ai)

*Strategy*

Open source is a strategy, not a charity. Survivability, the licences, and a history checked against its sources.

[← About](../about/index.md)[The writing →](../writing/index.md)

---

*This page is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).*
