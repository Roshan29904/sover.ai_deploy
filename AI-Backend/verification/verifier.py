from langchain_core.prompts import ChatPromptTemplate


def verify_response(llm, query: str, response: str) -> dict:

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are the verification component of a sovereign AI system.

Check whether the generated response satisfies the user's request.

Evaluate:
1. Does the response answer the user's request?
2. Did it follow explicit instructions such as length or format?
3. Does it contain obvious factual errors or unsupported claims?

Return exactly one of these formats:

PASS

or

FAIL: <short reason>
"""
        ),
        (
            "human",
            """
User request:
{query}

Generated response:
{response}
"""
        )
    ])

    result = (prompt | llm).invoke({
        "query": query,
        "response": response
    })

    verdict = result.content.strip()

    if verdict.startswith("PASS"):
        return {
            "verified": True,
            "reason": verdict
        }

    return {
        "verified": False,
        "reason": verdict
    }