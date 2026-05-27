# Prompt Caching — A Powerful Way to Save on Token Cost and Latency, If You Work with Large Prompts

Hey,

In this article I want to share my personal experience using **prompt caching** — a technique that kept my output quality completely consistent while dramatically cutting my API bill. We're talking a drop from roughly **$0.50 per query down to $0.05 per query**, or put another way: **96% of my input tokens got a 50% discount**.

I'll also walk you through a working CLI demo I built so you can see the numbers live in your own terminal — not a screenshot, not a made-up benchmark, your own real API responses with real token counts and real costs printed right after every query.

Let's get into it.

---

## First, Let's Talk Tokens — Because Not All Tokens Are Equal

Before prompt caching makes sense, you need to understand how LLM providers actually charge you.

There are two sides to every API call:

### Input Tokens
Everything you *send* to the model. This is not just the user's question. In any real AI application, your input has multiple layers:

```
┌─────────────────────────────────────────────────┐
│                   INPUT TOKENS                  │
├─────────────────────────────────────────────────┤
│  System Prompt       ← your AI's "personality"  │
│  Tool Definitions    ← functions the AI can use │
│  Conversation History← prior messages in context│
│  User Message        ← what the user typed now  │
│  Any extra context   ← RAG results, docs, etc.  │
└─────────────────────────────────────────────────┘
```

All of this gets tokenized and sent together. Every. Single. Call.

### Output Tokens
Everything the model *generates* in response. Fairly straightforward — the more the model writes, the more output tokens. Advanced reasoning models (like o1, o3) also generate internal "thinking tokens" that add to this count.

### Why This Matters for Your Wallet

OpenAI charges differently for input and output. Here are the current prices (mid-2025):

| Model | Input | Cached Input | Output |
|-------|-------|-------------|--------|
| gpt-4o | $2.50 / 1M tokens | $1.25 / 1M tokens | $10.00 / 1M tokens |
| gpt-4o-mini | $0.15 / 1M tokens | $0.075 / 1M tokens | $0.60 / 1M tokens |

Notice that column in the middle — **Cached Input**. That's what this article is about.

---

## The Real Problem: You're Paying to Read the Same Book Every Time

Here's the scenario that prompted me to look into this. I was building a customer-support bot for a SaaS product. The system prompt was massive — product documentation, pricing tiers, troubleshooting guides, API reference, support policies. Realistic stuff you'd actually put in production.

Every time a user asked *anything* — "what plans do you offer?", "how do I fix a connection timeout?", "can I get a refund?" — I was sending that entire 1,600-token system prompt to the API. Again. And again. And again.

Think of it like hiring a librarian who reads the entire encyclopedia front-to-back before answering every single question you ask them. The answer might take 10 seconds, but the encyclopedia read takes 5 minutes — and you pay for all of it, every time.

That's the inefficiency prompt caching fixes.

---

## What Prompt Caching Actually Does

Prompt caching lets the LLM provider store a snapshot of your prompt on their servers. When your next request starts with the exact same prefix, they reuse that snapshot instead of reprocessing it from scratch.

The result:
- **50% cheaper** on those cached tokens
- **Lower latency** because the model skips reprocessing the cached portion
- **Zero change to output quality** — the model sees the exact same context

OpenAI does this **automatically** for any prompt prefix longer than **1,024 tokens**. You don't add any special flags or headers. Send the same system prompt twice within the cache TTL (~5–10 minutes), and the second request will report cached tokens in the usage response.

Anthropic's Claude has explicit prompt caching via `cache_control` markers — you opt specific blocks in. OpenAI's version is implicit, which is both simpler and slightly less predictable.

---

## Let's See It in Real Numbers

I built a CLI demo that makes this concrete. It's a customer-support bot for a fictional SaaS called **DataFlow Pro**. The system prompt is ~1,600 tokens of real documentation: pricing, troubleshooting guides, API reference, support policies.

When you ask a question, the app shows you:

```
┌─────────────────────────────────────────────────────────────────┐
│ Response #2                                                     │
├─────────────────────────────────────────────────────────────────┤
│  ... answer from the bot ...                                    │
└─────────────────────────────────────────────────────────────────┘

 Metric                    Value       Details
 ─────────────────────────────────────────────────────────────────
 Latency                   1.73s       wall-clock time
 Input tokens (total)      1,643       system prompt + your query
 ↳ Cached tokens           1,487       91% of input — billed at 50% price
 ↳ Fresh tokens            156         your query, processed at full price
 Output tokens             89          response length
 ─────────────────────────────────────────────────────────────────
 Cost this query           $0.00028    with caching
 Cost without cache        $0.00046    what you'd normally pay
 You saved                 $0.00018    39% off this query
```

That 39% saving is on a tiny 1,600-token system prompt. In production, system prompts are routinely 20K–200K tokens. Scale the math up and you get that $0.50 → $0.05 drop I mentioned in the intro.

---

## The Demo App

Clone or copy the code, add your OpenAI key, and run it:

```bash
git clone https://github.com/tushar-sharma/medium-articles-tutorials
cd medium-articles-tutorials/Prompt_caching

cp .env.example .env
# → open .env and add your OPENAI_API_KEY

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py
```

### What you'll see on startup

```
╭──────────────────────────────────────────────────────────────────────────────╮
│  Prompt Caching Demo  — real numbers, real savings                           │
│                                                                              │
│  Model: gpt-4o-mini   System prompt: ~1,229 words                           │
│                                                                              │
│  How it works:                                                               │
│    OpenAI caches prompt prefixes longer than 1,024 tokens on their servers. │
│    Your first query pays full price and warms the cache.                     │
│    Every query after that gets 50% off on all those cached tokens            │
│    — and the model responds faster because it skips re-processing them.      │
│                                                                              │
│  Cached-input price: $0.075/1M tokens  (vs $0.150/1M full price)            │
│                                                                              │
│  Commands:  <question>   !compare <question>   !stats   !exit               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Three ways to use it

**1. Just ask something**

```
You › What plans do you offer?
```

First query — you'll see 0 cached tokens. The app tells you: *"Cache is now warm. Ask another question to see the difference."*

**2. Ask again (or anything else)**

```
You › How do I fix a connection timeout?
```

Same system prompt got reused. Now you'll see cached tokens > 0 and cost drops visibly.

**3. The `!compare` command — the real eye-opener**

```
You › !compare What's the difference between Business and Enterprise plans?
```

This runs the exact same query twice and shows you a side-by-side table:

```
╔══════════════════════════╦═══════════════════╦═══════════════════╦════════════════════════╗
║ Metric                   ║ Run 1  (no cache) ║ Run 2  (cached)   ║ Δ                      ║
╠══════════════════════════╬═══════════════════╬═══════════════════╬════════════════════════╣
║ Cached tokens            ║ 0                 ║ 1,487             ║ +1,487 tokens now free ║
║ Latency                  ║ 2.41s             ║ 1.73s             ║ 0.68s faster           ║
║ Cost                     ║ $0.00046          ║ $0.00028          ║ 39% cheaper            ║
║ Saved vs no-cache        ║ —                 ║ $0.00018          ║ 39% off                ║
╚══════════════════════════╩═══════════════════╩═══════════════════╩════════════════════════╝
```

Then it extrapolates:

```
╭──────────────────────────────────────────────────────────────╮
│  At scale — caching this system prompt saves:               │
│                                                              │
│   1,000 queries/day  →  $0.18/day saved  ($5/month)         │
│   10,000 queries/day →  $1.80/day saved  ($54/month)        │
│                                                              │
│  Real-world system prompts are often 10–100× bigger.        │
│  The bigger your static context, the more dramatic savings. │
╰──────────────────────────────────────────────────────────────╯
```

---

## How the Code Works

Here's the core of the cost calculation — nothing magical:

```python
PRICING = {
    "gpt-4o-mini": {
        "input":        0.150 / 1_000_000,   # $0.15  per 1M tokens
        "cached_input": 0.075 / 1_000_000,   # $0.075 per 1M tokens (50% off)
        "output":       0.600 / 1_000_000,   # $0.60  per 1M tokens
    },
}

def calc_cost(input_tokens, cached_tokens, output_tokens):
    p = PRICING["gpt-4o-mini"]
    fresh = input_tokens - cached_tokens

    actual   = fresh * p["input"] + cached_tokens * p["cached_input"] + output_tokens * p["output"]
    no_cache = input_tokens * p["input"] + output_tokens * p["output"]
    saved    = no_cache - actual

    return {"actual": actual, "no_cache": no_cache, "saved": saved}
```

And here's how we pull the cached token count from the API response — it's buried in `response_metadata`:

```python
def call_api(llm, user_input):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]

    t0 = time.perf_counter()
    response = llm.invoke(messages)
    elapsed = time.perf_counter() - t0

    usage   = response.response_metadata.get("token_usage", {})
    details = usage.get("prompt_tokens_details") or {}

    return {
        "response":      response.content,
        "input_tokens":  usage.get("prompt_tokens", 0),
        "cached_tokens": details.get("cached_tokens", 0),   # ← this is the key field
        "output_tokens": usage.get("completion_tokens", 0),
        "elapsed":       elapsed,
    }
```

The `cached_tokens` field in `prompt_tokens_details` is what OpenAI returns to tell you how many tokens it served from cache. If it's 0 on your first call and 1,400+ on your second — that's the cache working.

---

## The Numbers That Actually Got Me

Let me make the at-scale math explicit, because this is where it gets interesting.

Say you have a SaaS product with a 50,000-token system prompt (company knowledge base, legal docs, full product catalog — totally normal). You use gpt-4o.

**Without caching:**
```
50,000 tokens × $2.50/1M = $0.125 per query (system prompt alone)
+ user query ~500 tokens  = $0.00125
+ response ~1,000 tokens  = $0.01
─────────────────────────────────────
Total per query:  ≈ $0.136
```

**With caching (system prompt hits cache):**
```
50,000 tokens × $1.25/1M = $0.0625 per query (50% off)
+ user query ~500 tokens  = $0.00125
+ response ~1,000 tokens  = $0.01
─────────────────────────────────────
Total per query:  ≈ $0.074
```

That's a **46% drop** per query. At 10,000 queries/day:

| | Daily Cost | Monthly Cost |
|--|--|--|
| Without cache | $1,360 | $40,800 |
| With cache | $740 | $22,200 |
| **Savings** | **$620/day** | **$18,600/month** |

For a large enough context (200K+ tokens, which is within gpt-4o's context window), the savings become even more disproportionate because the cached portion dominates the total cost.

---

## When Does This Apply to You?

Prompt caching helps the most when:

1. **Your system prompt is large** (>1,024 tokens for OpenAI, which is about 750 words — most production prompts easily exceed this)
2. **You get multiple queries against the same system prompt** (customer support bots, coding assistants, document Q&A)
3. **Queries arrive frequently** — the cache TTL on OpenAI is ~5–10 minutes, so bursty traffic benefits most. A prompt accessed once a day won't stay warm.
4. **Your system prompt is static** — if you're dynamically constructing different system prompts for each user, caching is harder to leverage consistently

It helps the *least* when:
- Your system prompt is tiny (<1K tokens)
- Every query has a completely unique context
- Traffic is too sparse to keep the cache warm

---

## Key Takeaways

- **Input tokens ≠ just the user's message.** System prompt, tool definitions, conversation history all count — and in real apps, the system prompt is usually the biggest chunk.
- **OpenAI caches automatically** for prompts >1,024 tokens. No code changes needed. You just see it in the `prompt_tokens_details.cached_tokens` field.
- **Cached tokens cost 50% less** and arrive with lower latency — the model skips reprocessing them.
- **The bigger your static context, the bigger your savings.** A 1,600-token demo shows ~39% savings. A 200K-token production prompt can push that higher.
- **You can observe it directly** — run `!compare` in the demo and watch the token counts and costs change between run 1 and run 2.

---

## Try It Yourself

The full working demo is in this repo. All you need is an OpenAI API key.

```
Prompt_caching/
├── main.py          ← the CLI app
├── requirements.txt ← dependencies
└── .env.example     ← copy to .env, add your key
```

Run `!compare` with any question and you'll see the cache effect live.

If you're building anything with a large system prompt — a support bot, a coding assistant, a RAG pipeline, an agent with tool definitions — prompt caching is one of the easiest cost wins available to you right now. It doesn't change your architecture, doesn't change your output, and you don't have to do anything special to enable it on OpenAI.

---

*Written by Tushar Sharma. If you found this useful, check out the rest of the series at [medium-articles-tutorials](https://github.com/tushar-sharma/medium-articles-tutorials).*
