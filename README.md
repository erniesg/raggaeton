# RAGgaeton

RAGgaeton gives you a ReAct agent with ColBERTv2 retriever and Google search tools to answer questions about your business context!

On the roadmap: supercharge this with grid search over RAG params from document length to LLM model used. 🥳 🦾 🚀

# Demo
\[placeholder]

The TIA Bot above is playing in regular speed... After I have preloaded the index and agent. Actual behaviour will be slower - keep your eyes on the console to see what's going on!

It's thinking out loud because the custom prompt made it so, the default system prompt will not exhibit this behaviour. Probably fixable.

# How to Run Locally
- Clone the repository
- `cd` to the repository
- Recommended Python version: `3.10.6`
- Run the following command to install dependencies
```bash
pip install -r requirements.txt
```
- Create a `.env` file in the project root with the following keys provided to you:
```env
SUPABASE_KEY=...
SUPABASE_PW=...
OPENAI_API_KEY=...
MODAL_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_SEARCH_ENGINE_ID=...
```
- Run the following command
```python
uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level debug
```
- Wait for the application to finish initialising. You should see the message: `Lifespan: Components initialized successfully` in console

### Interacting with the API
- Visit the [raggaeton-frontend](https://github.com/erniesg/raggaeton-frontend) repository and follow the instructions there to interact with the API via the front-end

### Sample `curl` Request
- You can test the API with a sample `curl` request:
```bash
curl -X POST "http://127.0.0.1:8000/chat" -H "Content-Type: application/json" -d "{\"query\": \"What are the top startups in Indonesia?\"}"
```

### NOTE
- I only managed to ingest 900 posts despite multiple attempts so the knowledgebase is incomplete. Pages don't appear from 31 on. That seemed to be the limit?
- The default agent used is OpenAIAgent with custom prompts `raggaeton/raggaeton/backend/src/config/prompts.md` so the text response is rather funky. If it looks like it hasn't finished its train of thought, just say something to continue.
- The first time you load this, it will take a while to start, index and fetch data for the first time so you might want to view the console to view progress.
- You can rename `prompts.md` to `_prompts.md` then restart FastAPI to see default OpenAI agent behaviour (it still thinks it's 2013...).

# Implementation
![Architecture diagram](https://github.com/erniesg/raggaeton/blob/master/raggaeton/public/archi.png?raw=true)

This full-stack RAG project is structurally composed as above. We make use of `Vercel AI SDK`'s React Server Components and Streamable UI over `Gradio`/`Streamlit` for a more enjoyable UX.

In terms of the main RAG engine, I went with LlamaIndex as it seemed to be more specialised for search and retrieval in particular and its abstractions are more useful than LangChain for development.

Once the main framework has been decided, my scaffold was to break the project into a few major modules which will encapsulate all relevant logic within, the `raggaeton/backend/src/api/endpoints` folder contains the below core RAG logic:
* `ingest.py` for ingesting source documents with metadata and persistence locally
* `index.py` is responsible for index creation for documents for efficient retrieval
* `chat.py`makes use of `agent.py` with `tools.py` to initialise our desired ReActagent behaviour with tools and instantiates a FastAPI app <--- This is the one we're going with
* `create_chat.py`is an implementation of a straightforward `chat_engine `setup with various embedding models

Other supporting modules include:
* `raggaeton/backend/scripts` folder contains the modal scripts ran to deploy this with scalable serverless resources such as downloading documents and preprocessing the HTML into markdown for easier LLM consumption
* `common.py` to do config loading and path resolution
* `supabase.py` for CRUD operations on a `postgresql` instance
* `utils.py` to house some handy utilities and minor functions

Within the time constraint, I wanted to make `raggaeton` flexible enough to allow for different experimental variations which I deem as critically important for performing grid search over hyperparameters in an actual production system while delivering a valuable enough suite of end user functionalities given the context of the assignment; like any impossible trinity, code quality suffered as a result like. Let's look at some interesting trade-offs made in the next section.

### Cost <> System Performance
 A full-stack RAG system presents multiple points for possible optimisation, from the way documents are chunked to the system prompts used. There are a few critical points I focused on for this project and my decisions about which LLM, indexing and retrieval methods to use will be detailed below.

 In terms of LLM selection which will serve as the main reasoning and answering brainpower of our app, the key choice was to make `raggaeton` compatible with both OpenAI and Anthropic. This gives our system more resilience and prevents vendor lock-in in case of uncontrollable API failures or regressions.

As for indexing and retrieval, my key consideration was to simplify the number of steps involved for latency reasons - making retrieval as effective as possible hence reranking will not be needed. I settled on `ColBERTv2` as it offers token-level comparisons (rather than compressing a document into 1 single vector) and is retrieval-optimised to for scalable "[BERT-based search over large text collections in tens of milliseconds](https://huggingface.co/colbert-ir/colbertv2.0)". Arguably, it's the most cutting-edge research work that is just making its way into adoption and production so I am optimistic about its growth trajectory.

These key decisions and how they were derived are explained in greater detail below.

#### LLM Selection
 My initial hypothesis was to use the `claude-3-haiku-20240307` for production inference as it is blazingly fast and cheap of all the available LLMs but an initial test of its agent capabilities was dissatisfactory with it giving irrelevant answers while `claude-3-opus-20240229` and `gpt4-o` were up to the job so I ended up defaulting to `gpt4-o` anyway as OpenAI's LLMs are most comprehensively supported in the ecosystem. Maybe it'll be worth a revisit when Anthropic makes their models available for fine-tuning.

#### Indexing & Retrieval
`raggaeton` supports embedding and indexing generation by simply changing the `config.yaml` with your desired HuggingFace embedding model. Initially, I shortlisted a few models based on their MTEB performance as below as I wanted to test with different embedding sizes:
* `Alibaba-NLP/gte-base-en-v1.5`: 768
* `Alibaba-NLP/gte-large-en-v1.5`: 1024
* `WhereIsAI/UAE-Large-V1`: 1024
* `GritLM/GritLM-7B`: 4096

The idea was also that these open source models would allow for fine-tuning of a custom embedding that best knows our documents. Unfortunately, the LlamaIndex Supabase vector store integration only supported up to 768 when I tested it so it seemed kinda pointless.

That was when I decided to give `ColBERTv2` which seems more experimental and is not widely supported by all vector databases yet (it's only supported by Vespa and Qdrant has it on the roadmap) a try. Other people's experiments \[[1](https://www.linkedin.com/pulse/guidebook-state-of-the-art-embeddings-information-aapo-tanskanen-pc3mf/)]  and its use as a reranker gave me confidence that this will suit our needs.

### Rapid Iteration & Deployment
Since so many points on an end-to-end RAG app is possible for optimisation and transformers have proven that machines can perform such optimisations much better than humans, `raggaeton` was designed with a goal to allow for grid search and leverage serverless compute for hyperparameter tuning, i.e. suppose we want to test different configurations as below:
- `docment_length`: \[256, 512, 1024]
- `chunk_size`: \[128, 256, 512]
- `embedding_model`: \[... any 3]
- `dimensions`: \[512, 1024, 4096]
- `llm`: \[... any 3]

We will have 243 variations that we can run against a standard test set of questions with varying levels of difficulty, comparing latency and retrieval effectiveness, with tools such as `deepeval`. This will only be possible with a service like Modal.

That is the desired end state, and we are part of the way there for reasons to do with the challenges I encountered along the way which I will describe next.

# Challenges
Maybe one of the most exciting (and challenging) aspect of doing AI engineering is that it's so new with so many new techniques, toolings and processes constantly on the horizon that everyone KAN be both an expert and a beginner all at once, all the time.

What I find to be especially interesting about building in this space is also that many a times, the best way to test a hypothesis is to simply build it. Vibe checks from the community and public leaderboards can be good jumping off points, but nothing beats implementing and testing something for your use case yourself.

In this spirit of sharing and failing in public, I will discuss the key challenges I faced next.

### Abstraction vs. Specification
This is something I always struggle with and the peace I've found with it is to just live with the trade-off, as uneasy as it gets, or perhaps until I become a better programmer and a clearer thinker... Intuitively test-driven development makes a lot of sense and I can go to sleep better at night knowing that my deployments pass existing tests, but over-abstracting too early is how I ended up with this unnecessarily extensive folder structure at this stage.

If I want my entire system to be perfectly planned out with minimal if not zero duplication of logic, all functions and modules fully reusable and responsible for one single thing, it will never get built. What tends to happen along the way is also that there are many software or hardware limitations and unexpected user behaviours so rather than a utopian release that will never happen, I try to:
* Roll-out something that will satisfy a minimal use case so I can quickly get feedback and test reception
* Incorporate within it just-enough room for expansion, abstraction and testing; I may not be able to cover all bases but I should know where and how my system will fail exactly (as much as possible)
* Often when trying to achieve the first point within a time limit, code gets written that is not the most thoughtful kid on the block. For the purpose of an assignment or something that I am not charging people money for, I tend to just move on as long as it works. Subsequently in the process of development, whenever I find myself encountering the same issue or writing similar code at least thrice, that's when I know I have something that needs to be better thought-out and refactored first by writing a new implementation that will resolve all similar issues moving forward, then slowly replace old components with the new one one by one...

### Building a Mental Model for Modal
I really like Modal because I think it solves a real problem. I'm always a champion for products and services that dares to design backwards from how things should be rather than settle for a compromise with the status quo of how things are. For example, with Docker.
![Docker Image](https://erikbern.com/assets/docker.jpeg)

Maybe another way to think about it is that it's an abstraction layer on top of containerisation technologies that offer data scientists, AI and ML engineers the hard-to-come-by delight of focusing on your pipelines and logic because web deployment, client-server interactions, secrets, serialisation and deserialisation, async, promise, WebSockets... What is even all these nonsense?

The problem now though is that the need for fully reproducible environments between local and remote do not go away. And instead of landing my port on Docker, I still have to grasp and wrestle with how Modal handles deployment for you. I ran into challenges with passing my custom package to the remote computer, pathing, scope and availability of my custom functions, and state handling for deployed ASGI apps persistently. There are some quirks to Modal such as:
* File uploads are of a certain size and timeout limit so you won't be able to upload huge videos and leverage cloud functions to transcribe, for example.
* I can mount a local package into a function, but not into an image? So if my function is mounted with an image and my local package, will it be available whenever the `app.function()` decorator is used? Or perhaps I should mount everything onto the App? Only way to find out is to test it out.
* I was expecting `modal deploy modal_chat.py` to initialise only happen once and that same agent to be available throughout until the app is shutdown. But the `/chat` endpoint I deployed would ALWAYS start the ASGI app which rebuilds my index and agent whenever a `POST` request is made, maybe because of the way that Modal serves serverlessly.

The nesting of local imports looks unwieldy and the bundling of deployment to Modal's infrastructure also made me realised why the lift and shift paradigm is still dominant. While Modal speeds up my development, bumps along the way like the ones listed above took longer than is necessary to resolve as I wasn't able to just connect into the remote computer and see what's going on interactively. But of course that is precisely why virtual machines incur a certain cost.

Moving forward, I think I just need to develop a better mental model for Modal and figure out some repeatable design patterns to separate deployment from application logic, so that we are not married to the platform per se.

### Where My Imports at?
While Modal abstracts away access to compute and GPU, LlamaIndex abstracts the building of RAG applications. This is my first time building with it and I particularly liked that a pipeline can simply be defined as such:
```python
pipeline = IngestionPipeline(
    node_parser=MarkdownNodeParser(),
    docstore=SimpleDocumentStore(),
    vector_store=vector_store,
    embedding_model=embed_model,
    ingestion_cache=IngestionCache(),
)
```

Run it and you can start to query or chat with your documents more or less right away!

But, the theme and refrain of abstractions are not news at this point in software history. The relationship between components are not extensively documented and file structures have changed enough such that I spend a reasonable amount of time just trying to figure out what is the current import path for what I needed. Like that question about mounts and images and functions with Modal, I spent a lot of time looking around the codebase to figure out if a custom retriever or query engine can be passed to the ReAct chat engine that I wanted to use. The problem was that it requires a different construction to how other chat engines were customised and my solution was to wrap the ColBERTv2 retriever as a query engine tool and pass it along with Google Web Search as tools to the `OpenAIAgent` and `ReActAgent`.

There were mental gymnastics I got entangled in such as: so if a router can be a retriever (for example, the LLM can route queries to a summary index or a vector index, depending on the question asked), and a router can also be a query engine, the former pertains to routing to different data sources only while the latter pertains to routing to different possible tools in which a retriever is also a tool? Or...? How do query engines, tools, retrievers and chat engines relate to each other? What is the set relationship, dependency and methods one can use that another cannot?

These challenges are entirely to be expected of a field that is so young and moving so quickly that we just don't have settled building blocks or even a vocabulary, yet. In reality every company's implementation will have to be tailored to own use cases and constraints and I expect some common design patterns to emerge as more AI-native products find mass adoption. Life will be a lot easier then. But this build-it-to-test-it phase is incredibly fun too.

### Deployment Woes
All it took was packaging my app into Docker to make me miss Modal again. While most Modal deployments took less than 60s to finish, Docker is just so slow and it does not help at all that I am trying to build and pull images from behind a VPN in China at time of typing.

Maintaining the agent's state was a real challenge because it's non-serialisable (tried `Pickle`, `Dill` and `Joblib` - none worked) and I cannot simply pass it around as a global variable. It has to actually be instantiated - so the workaround I came up with was to use FastAPI Lifespan Event to load the tools and index once at start-up to "create" the agent. I'm sure there are better ways to handle this and this really goes back to how and why mature APIs like OpenAI handles a lot of heavylifting for us. In the agentic space, I'll be watching closely for better solutions.

# Areas for Improvement

### Project Roadmap and Enhancements
For the project, the following are key areas for further work:
* Better caching and integration with custom prompt

While I customised a system prompt in `prompts.md` and you can play with it to see the model "think out loud" - it's definitely feasible to stream the intermediate responses in a much more interesting way. Also caching of frequent responses will probably help to speed things up a lot more in production (and save on costs too).

* Deployment With a Fine-tuned Model for Routing

In production, it might be meaningful to fine-tune a small and cheap model that answers straightforward queries, does routing and making parallel calls *very well* for an optimal user experience.

* More Tools

This then means that we can increase the number of tools available to the LLM, query rewriting, decomposition, calling on other data sources and so on.

* Enrich and Enhance Datasets for RAG

Speaking of datasets, I did not incorporate other data per se since LLMs are already trained on an entire Internet's worth of data. Also for Tech in Asia's posts, I kept running up against a 900 posts limit. Down the road, it is worth looking at enriching existing datasets for better LLM access, or tap into more local data sources.

* Grid Search + Evals

Parts of an experimentation engine is already set up, so this area is definitely ripe for an actual field test to find the best settings for our own purposes coupled with evaluations to "unit test" our agent!

### Reverse Engineer from Human Evaluation
There were a few times on this project that I got too carried away on exploring my own pedantic curiosity that I didn't end up using which were time taken away for checking off the dimensions of creativity, quality of prompts, reliability and good documentation fully. In retrospect, I should have better clarified the weightage and expectations to better ensure that what I deliver will meet expectations.

Grid search, a more delightful UX and web deployment were areas that took up a lot of my effort aside from the core work of an effective RAG engine and they don't map to the full set of dimensions that I'll be graded upon well. :( But I had lots of fun which is a reward in its own right.

My stance on prompting vs. programming is like my lean towards hyperparameter tuning with grid search: let the LLM do it. It is necessary but it is something that I like to ask the LLM to do for me in particular. Good prompts are obviously necessary but natural language is highly imprecise and any system that relies on prompting effectiveness to be good feels especially brittle to me. The main motivation in letting LLMs handle this is to structure and constrain such non-deterministic programmes to be as backward-compatible with software and be more like programming, rather than whispering black magic, as much as possible. It is for this reason that for future extensions of RAGgaeton, I'd like to explore DSPy and/or Instructor further!

### Better Hierarchal Planning
Related to the first point, a clearer scope would have informed much better hierarchal planning on my part to bind myself to requirements more strictly. From first commit
`741de71fe28f4d29296e7c48e5cb77e47560b315 Wed May 29 13:30:33 2024 +0800` till deadline, I had 5 days to work on this and in retrospect, I just feel like I hadn't optimised my time for the evaluation per se. In fact, I was optimising for my own learning and exploration because I can guarantee the certainty of this outcome (my own enjoyment) a lot better than a "subjective" evaluation so yea.  Rather than invest my time in building something for an outcome that is uncertain in nature, the reward of gratification from learning is far more certain and indeed, I enjoyed the process tremendously despite the challenges encountered. This is just a bit of meta-reflection that it might not have been the best use of time from a job-seeking perspective.

Still, from a pragmatic point of view, I probably should not have spent as much time on grid search and wrestling with the `Vercel AI SDK` in JavaScript, a Third Language to me, as I did. Again, these are all areas that could have been improved with better understanding of requirements and planning.

### Better Abstractions and Mental Models
Obviously, a lot of the challenges and time constraints would be no issues if I could abstract better and work much more effectively. Clearer mental models and design patterns will help in organising and writing code more elegantly though I think it's also important to note that while JavaScript came out 28 years ago, GPT-4 is only about 1 year old. While agile development and DevOps have been around and lessons can be borrowed, I do think that there's an extent to which old lessons don't apply here because deterministic programmes are a different beast to probabilistic programmes with data at its heart. The best way to improve in this area is to connect with a community, share and learn continuously, which is why I enjoy A.I. engineering meet-ups and the LLM fine-tuning course that I'm doing right now. I find it very valuable to learn to A.I. podcasts when running to keep myself informed and updated too.

Last but not least, working in a team will no doubt help everyone to better offload parts of the stack (say, JavaScript) in order to cultivate deep expertise so this is something I'll be looking forward to as well!
