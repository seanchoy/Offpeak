"""Score a retriever against hand-labelled queries."""
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Share of the relevant slugs that appear in the top k (练习册 Part 6.1)."""
    if relevant == set():
        raise ValueError("`relevant` must not be empty.")

    count = 0
    for s in relevant:
        if s in retrieved[:k]:
            count += 1

    return  count/len(relevant);


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """1 / position of the first relevant slug, 0.0 if none (练习册 Part 6.1)."""


    n = len(retrieved)
    for i in range(0, n):
        if retrieved[i] in relevant:
            return 1/(i+1)

    return 0.0



def rrf_fuse(
    rankings: list[list[str]], k: int = 60, weights: list[float] | None = None
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: [(slug, score)] best first (练习册 Part 6.2)."""
    if weights is None:
        weights = [1] * len(rankings)

    if len(rankings) != len(weights):
        raise ValueError("The rankings and weights must have the same length.")

    slug = {}

    for ranking, weight in zip(rankings, weights):
        for rank, title in enumerate(ranking, start = 1):
            if slug.get(title):
                slug[title] += weight/(k+rank)
            else:
                slug[title] = weight/(k+rank)

    result = [(title, rank) for title, rank in slug.items()]
    return sorted(result, key =lambda pair: (-pair[1], pair[0]))




@dataclass(frozen=True)
class QueryResult:
    query: str
    retrieved: list[str]
    recall: float
    reciprocal_rank: float


@dataclass(frozen=True)
class EvalReport:
    recall: float
    mrr: float
    per_query: list[QueryResult]


def evaluate(
    search: Callable[[str, int], list[str]], golden: list[dict], k: int = 5
) -> EvalReport:
    """Run every golden query through `search` and average the metrics (练习册 Part 6.5)."""
    if golden is None:
        raise ValueError("`golden` must not be None.")

    per_query = []

    for querys in golden:
        retrieved = search(querys["query"], k)
        relevant = set(querys["relevant"])

        recall = recall_at_k(retrieved, relevant, k)
        reciprocal = reciprocal_rank(retrieved, relevant)
        per_query.append(QueryResult(querys["query"], retrieved, recall, reciprocal))

    recall_avg = mean(query.recall for query in per_query)
    mrr = mean(query.reciprocal_rank for query in per_query)

    return EvalReport(recall=recall_avg, mrr=mrr, per_query=per_query)






