from services.retrieval import graph_search

try:
    print(graph_search("Type 2 Diabetes"))
except Exception as e:
    import traceback
    traceback.print_exc()
