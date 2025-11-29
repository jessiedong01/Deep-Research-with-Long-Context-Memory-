An agent that can do deep, multi-step research by creating and using a structured memory system instead of relying only on raw long-context prompts. The agent reads documents, generates table schemas, extracts information into those tables, and then answers complex questions by querying its own structured memory.

The goal is to show that LLMs can research topics over long horizons, track information over time, and synthesize details across many documents. This helps in domains like:

- hedge fund and investment research

- scientific literature review

- policy analysis

- any task requiring long-document reasoning or multi-source synthesis

What the system does:

- Reads documents and identifies what information needs to be tracked

- Creates relational schemas (tables, columns, relationships)

- Extracts details from text and populates those tables

- Builds hierarchical research plans (outlines, stages, summaries)

- Answers hard questions using the structured memory rather than raw context


Traditional long-context LLMs struggle with:

- retrieving old details

- tracking entities over time

- connecting information across multiple sources

- answering extremely specific, multi-document questions

Structured memory helps overcome this by giving the model a persistent, queryable knowledge base.
