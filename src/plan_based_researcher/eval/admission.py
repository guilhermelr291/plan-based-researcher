"""Clip judge rankings to artifact hits and apply champion-only uniqueness (ADM-03, ADM-04)."""

from __future__ import annotations

from dataclasses import dataclass

from plan_based_researcher.eval.types import PaperKey, SearchWaveJudgement

__all__ = [
    "FinalSearchVerdict",
    "apply_u1",
    "champion_keys",
    "clip_ranked_keys",
    "finalize_wave_rankings",
    "hit_key",
]


def hit_key(hit: dict) -> tuple[str, str]:
    """(arxiv_id, str(version))."""
    version = hit.get("version")
    return (str(hit["arxiv_id"]), str(version) if version is not None else "")


def clip_ranked_keys(ranked: list[PaperKey], hits: list[dict]) -> list[PaperKey]:
    """Keep keys present in this artifact's hits, preserve judge order, drop hallucinations.
    If PaperKey.version is empty, bind to the unique hit with that arxiv_id when exactly one exists; otherwise drop.
    If version is non-empty, keep iff (arxiv_id, version) appears in hits.
    Dedupe by (arxiv_id, version) keeping first occurrence.
    Return PaperKey with bound version filled in."""
    by_id: dict[str, list[tuple[str, str]]] = {}
    present: set[tuple[str, str]] = set()
    for hit in hits:
        if not isinstance(hit, dict) or not hit.get("arxiv_id"):
            continue
        pair = hit_key(hit)
        present.add(pair)
        by_id.setdefault(pair[0], []).append(pair)

    clipped: list[PaperKey] = []
    seen: set[tuple[str, str]] = set()
    for key in ranked:
        if key.version == "":
            matches = by_id.get(key.arxiv_id) or []
            if len(matches) != 1:
                continue
            bound = PaperKey(arxiv_id=key.arxiv_id, version=matches[0][1])
        else:
            pair = (key.arxiv_id, key.version)
            if pair not in present:
                continue
            bound = PaperKey(arxiv_id=key.arxiv_id, version=key.version)
        bound_pair = (bound.arxiv_id, bound.version)
        if bound_pair in seen:
            continue
        seen.add(bound_pair)
        clipped.append(bound)
    return clipped


def champion_keys(artifacts, passed_steps, plan) -> set[tuple[str, str]]:
    """Ranking head (ranked_keys[0]) of every passed SEARCH artifact already on the plan.
    artifacts: dict[str, artifact]; ranked_keys entries are dicts with arxiv_id/version.
    Skip non-search plan steps. Missing artifact or empty ranked_keys → skip."""
    champions: set[tuple[str, str]] = set()
    if not isinstance(plan, list) or not isinstance(artifacts, dict):
        return champions
    for index in passed_steps:
        if not isinstance(index, int) or index < 0 or index >= len(plan):
            continue
        step = plan[index]
        if not isinstance(step, dict) or step.get("agent") != "search":
            continue
        artifact = artifacts.get(str(index))
        if not isinstance(artifact, dict):
            continue
        ranked = artifact.get("ranked_keys") or []
        if not isinstance(ranked, list) or not ranked:
            continue
        head = ranked[0]
        if not isinstance(head, dict):
            continue
        arxiv_id = head.get("arxiv_id")
        if not arxiv_id:
            continue
        version = head.get("version")
        champions.add((str(arxiv_id), str(version) if version is not None else ""))
    return champions


def apply_u1(ranked: list[PaperKey], assigned: set[tuple[str, str]]) -> list[PaperKey]:
    """Drop keys whose (arxiv_id, version) is already in assigned. Preserve order."""
    return [key for key in ranked if (key.arxiv_id, key.version) not in assigned]


@dataclass(frozen=True, slots=True)
class FinalSearchVerdict:
    step_index: int
    passed: bool
    plan_inadequate: bool
    feedback: str
    ranked_keys: list[PaperKey]


def finalize_wave_rankings(
    wave, plan, artifacts, passed_steps, judgement: SearchWaveJudgement,
) -> list[FinalSearchVerdict]:
    """
    wave: list[int] step indices in this wave (already plan order, but still process in plan order:
          for i in range(len(plan)) if i in wave_set).
    assigned seed = champion_keys of passed_steps whose index is NOT in this wave.
    For each wave step in plan order:
      get judge SearchStepVerdict for that index (match judgement.verdicts by step_index)
      hits = artifacts[str(i)]['hits'] (empty if missing)
      ranked = verdict.ranked_keys if verdict else []
      clipped = clip_ranked_keys(ranked, hits)
      unique = apply_u1(clipped, assigned)
      if unique: passed=True; assigned.add(head only)  # (head.arxiv_id, head.version)
      else: passed=False
      copy plan_inadequate and feedback from the judge verdict; if no verdict, plan_inadequate=False and feedback=""
    Do NOT call an LLM. Do not import graph nodes.
    """
    wave_set = set(wave)
    seed_steps = [index for index in passed_steps if index not in wave_set]
    assigned = champion_keys(artifacts, seed_steps, plan)
    verdicts = {item.step_index: item for item in judgement.verdicts}
    artifacts_map = artifacts if isinstance(artifacts, dict) else {}
    results: list[FinalSearchVerdict] = []
    for index in range(len(plan)):
        if index not in wave_set:
            continue
        verdict = verdicts.get(index)
        artifact = artifacts_map.get(str(index))
        raw_hits = artifact.get("hits") if isinstance(artifact, dict) else None
        hits = [hit for hit in raw_hits if isinstance(hit, dict)] if isinstance(raw_hits, list) else []
        ranked = list(verdict.ranked_keys) if verdict is not None else []
        unique = apply_u1(clip_ranked_keys(ranked, hits), assigned)
        if unique:
            passed = True
            head = unique[0]
            assigned.add((head.arxiv_id, head.version))
        else:
            passed = False
        if verdict is not None:
            plan_inadequate = verdict.plan_inadequate
            feedback = verdict.feedback
        else:
            plan_inadequate = False
            feedback = ""
        results.append(
            FinalSearchVerdict(
                step_index=index,
                passed=passed,
                plan_inadequate=plan_inadequate,
                feedback=feedback,
                ranked_keys=unique,
            )
        )
    return results
