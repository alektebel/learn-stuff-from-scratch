"""Mutation tests for the RAG project-4 contextual-chunking checker.

Each entry is a classic mistake for one mechanism: the exact text is planted into a copy of
the solutions and the named check step must report a failure (✗). Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        rag-from-scratch/chunking rag-from-scratch/chunking/_build/mutations.py

Every mutated step runs on a hand-built corpus, so the harness works in a bare temporary
directory without the shared eval set or the sibling ``../bm25`` (step 4's validity and
distinctness assertions are the self-contained half of that step).
"""

MUTATIONS = [
    # The trailing partial chunk is dropped, so the chunks no longer reach the end of the
    # body (step 1 requires the last chunk's end to equal len(body)).
    (
        "chunk_document drops the last partial chunk",
        "chunking.py",
        "        chunks.append(Chunk(_chunk_id(doc_id, index), doc_id,\n"
        "                            body[start:end], start, end))\n"
        "        index += 1\n"
        "        if i >= total:\n"
        "            break",
        "        if i < total or (end - start) >= size:\n"
        "            chunks.append(Chunk(_chunk_id(doc_id, index), doc_id,\n"
        "                                body[start:end], start, end))\n"
        "            index += 1\n"
        "        if i >= total:\n"
        "            break",
        "1",
    ),
    # The contextual prefix is omitted, so the chunk is indexed as a bare passage and the
    # section-path term the intended document relies on disappears (step 3).
    (
        "contextualise omits the title/section prefix (plain context)",
        "chunking.py",
        '    title = str(doc.get("title", ""))\n'
        '    return f"{title}. {section_path(doc)}. {chunk.text}"',
        "    return chunk.text",
        "3",
    ),
    # section_path becomes a constant, so no chunk carries its discriminative label and
    # the intended document cannot be recovered (step 3).
    (
        "section_path returns a constant label",
        "chunking.py",
        '    department = str(doc.get("department") or "general")\n'
        '    topics = _metadata_list(doc.get("topics"))\n'
        '    topic = topics[0] if topics else "general"\n'
        '    return f"{department}: {topic}"',
        '    return "section"',
        "3",
    ),
    # retrieve forgets to reduce the chunk ranking to distinct documents, so a document
    # answered by several chunks appears more than once (step 4).
    (
        "retrieve returns the same doc_id repeatedly (no distinct)",
        "chunking.py",
        "    ranked = _rank_chunks(query, k, chunk_index)\n"
        "    seen = set()\n"
        "    documents = []\n"
        "    for item in ranked:\n"
        '        doc_id = chunk_index["chunk_doc"].get(item["doc_id"])\n'
        "        if doc_id is None or doc_id in seen:\n"
        "            continue\n"
        "        seen.add(doc_id)\n"
        "        documents.append(doc_id)\n"
        "    return documents",
        "    ranked = _rank_chunks(query, k, chunk_index)\n"
        "    documents = []\n"
        "    for item in ranked:\n"
        '        doc_id = chunk_index["chunk_doc"].get(item["doc_id"])\n'
        "        if doc_id is None:\n"
        "            continue\n"
        "        documents.append(doc_id)\n"
        "    return documents",
        "4",
    ),
    # retrieve manufactures a document id that belongs to no corpus (step 4 rejects any
    # id outside the corpus).
    (
        "retrieve returns documents not in the corpus",
        "chunking.py",
        "        seen.add(doc_id)\n"
        "        documents.append(doc_id)\n"
        "    return documents",
        "        seen.add(doc_id)\n"
        "        documents.append(doc_id)\n"
        '    documents.append("GHOST")\n'
        "    return documents",
        "4",
    ),
    # The no-match case returns the whole index instead of abstaining (step 6 requires a
    # no-answer query to stay empty).
    (
        "abstention returns all chunks",
        "chunking.py",
        "    ranked = _rank_chunks(query, k, chunk_index)\n"
        "    seen = set()",
        "    ranked = _rank_chunks(query, k, chunk_index)\n"
        "    if not ranked:\n"
        '        ranked = [{"doc_id": entry["doc_id"]} for entry in chunk_index["entries"]]\n'
        "    seen = set()",
        "6",
    ),
]
