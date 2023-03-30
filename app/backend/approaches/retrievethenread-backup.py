import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from text import nonewlines

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class RetrieveThenReadApproach(Approach):

    template = \
"You are an intelligent assistant helping company employees with their solve their technical and financial  questions, and questions about the employee handbook.  " + \
"Use 'you' to refer to the individual asking the questions even if they ask with 'I'. " + \
"Answer the following question using only the data provided in the sources below. " + \
"For tabular information return it as an html table. Do not return markdown format. "  + \
"Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. " + \
"In what language do you ask a question and in what language do you reply. " + \
"If you cannot answer using the sources below, say you don't know. " + \
"""

###
Question: 'What is Azure Open AI?'

Sources:
info1.txt: The Azure OpenAI service allows access to OpenAI's powerful language models, including GPT-3, Codex, and Embeddings model families, through the REST API. These models can be easily adapted to specific tasks, including but not limited to content generation, summarization, semantic search, and natural language-to-code transformation. Users can access the service in Azure OpenAI Studio through the REST API, Python SDK, or Web-based interface.
info2.pdf: Azure OpenAI is an OpenAI service for enterprise customers that provides advanced large language modeling (LLM) and image generation technologies.
info3.pdf: Microsoft is committed to advancing AI in accordance with the principle of "putting people first". Generative models, such as those provided in Azure OpenAI, offer significant potential benefits, but without careful design and a full range of mitigation measures, such models have the potential to generate incorrect and even harmful content.
info4.pdf: Azure OpenAI services provide customers with high-level language AI through the OpenAI PGT-3, Codex, and DALL-E models, and enable the security and enterprise vision of Azure. Azure OpenAI co-develops apis with OpenAI to ensure compatibility and smooth transitions between the two.

Answer:
Azure OpenAI is an OpenAI service for enterprise customers that offers advanced large language modeling (LLM) and image generation technologies, as well as complete AI solutions and complete PaaS services. It offers features similar to OpenAI, including the latest models, security and data privacy, compliance, reliability, and accountable AI. [info2.pdf][info4.pdf].

###
Question: '{q}'?

Sources:
{retrieved}

Answer:
"""

    def __init__(self, search_client: SearchClient, openai_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, q: str, overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        prompt = (overrides.get("prompt_template") or self.template).format(q=q, retrieved=content)
        completion = openai.Completion.create(
            engine=self.openai_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0.3, 
            max_tokens=1024, 
            n=1, 
            stop=["\n"])

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
