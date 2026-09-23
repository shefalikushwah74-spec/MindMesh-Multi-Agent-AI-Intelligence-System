from agents import search_agent, reader_agent, writer_chain, critic_chain


def run_pipelines(topic: str) -> dict:
    state = {}

    # search agent working
    print("\n" + "=" * 50)
    print("step 1 - search agent is working...")
    print("=" * 50)

    build_search_agent = search_agent()

    search_Result = build_search_agent.invoke({
        "messages": [
            ("user", f"Find recent, reliable and detailed information about: {topic}")
        ]
    })

    state["search_results"] = search_Result["messages"][-1].content

    print("\nsearch result:", state["search_results"])


    # step 2 -- reader agent
    print("\n" + "=" * 50)
    print("reader agent is scraping top resources...")
    print("=" * 50)

    build_reader_agent = reader_agent()

    reader_Result = build_reader_agent.invoke({
        "messages": [
            (
                "user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search results:\n{state['search_results'][:800]}"
            )
        ]
    })

    state["Scraped_content"] = reader_Result["messages"][-1].content

    print("\nScraped content:", state["Scraped_content"])


    # step 3 -- writer chain
    print("\n" + "=" * 50)
    print("writer is drafting the report...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{state['Scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })
    print("\n drafted report:", state["report"])


    # step 4 -- critic report
    print("\n" + "=" * 50)
    print("critic is reviewing the report...")
    print("=" * 50)

    state["feedback"] = critic_chain.invoke({
        "report": state["report"]
    })
    print("\n critic report :", state["feedback"])

    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ")
    run_pipelines(topic)