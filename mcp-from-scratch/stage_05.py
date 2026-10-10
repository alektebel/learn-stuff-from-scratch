"""MCP From Scratch — stage 5: resources, prompts, and the three ways a name is missing

Stage 4 registered tools, which a client CALLS. This stage registers the two
features beside them — a resource, which a client READS, and a prompt, which a
client asks the server to fill in — and uses them to nail down something the tool
table hid: "the name you sent is not one I have" is three different statements,
and only one of them is -32002.

SPEC — MCP 2025-06-18:

    resources/list  {cursor?}          -> {"resources": [{"uri", "name",
                                          "mimeType"}], "nextCursor"?}
    resources/read  {uri}              -> {"contents": [{"uri", "mimeType",
                                          "text"}]}
    prompts/list    {cursor?}          -> {"prompts": [{"name", "description",
                                          "arguments"}], "nextCursor"?}
    prompts/get     {name, arguments?} -> {"description"?, "messages": [{"role",
                                          "content": {"type": "text", "text"}}]}

Codes this stage is allowed to put on the wire:

    -32602 invalid params      a cursor that is not a page of this list, an
                               unknown PROMPT name (`data: {"name": ...}`), a
                               missing or undeclared prompt argument;
    -32002 resource not found  `resources/read` of an unknown URI
                               (`data: {"uri": ...}` — the spec's own example);
    -32603 internal error      a loader that raises or returns a non-string, a
                               builder that renders something that is not a
                               valid message — the envelope adds this one, the
                               stage does not.

DESIGN DECISION — "not found" answers a different question depending on what was
looked up, so it does not always use -32002.
    A resource URI is an ADDRESS the server owns: the client named something by
    its global identifier and the server is the authority on whether it exists,
    and the spec gives exactly that failure its own code with the URI in `data`.
    A prompt name is a PARAMETER of `prompts/get`: the client passed a value to a
    method, the value is wrong, and that is -32602 with the name in `data` —
    exactly like an unknown tool name in stage 4. Answer -32602 for a missing
    resource and the client's routing layer, which keys on the code, tells the
    user "your request was malformed" about a resource that simply is not there;
    answer -32002 for a missing prompt and it goes hunting for a resource that
    never existed. The one thing both must NOT do is invent a fourth meaning for
    "no".

DESIGN DECISION — look the name up first, run the loader second.
    `Resource.read()` is the only place a loader is ever called, and read() is
    reachable only through a `Resource` the registry already holds. A registry
    that walks its loaders looking for the one that *would* serve the URI turns
    the caller's typo into an I/O operation — and, in a real server, into a read
    of a path nobody asked for. Registration is the whitelist, so it has to be
    consulted before anything else happens, or it is decoration.

DESIGN DECISION — a loader's failure is the server's error, not the client's.
    Three things can go wrong on the way to a resource's text, and all three are
    the server's fault: the loader raises (a file vanished, a database is down),
    the loader returns bytes or None where the spec says text, and a builder
    renders something that is not a message. None of that is the client's doing,
    so none of it is -32602: they propagate, the envelope turns them into -32603
    whose message names the exception TYPE, and the client learns the server
    broke without learning how. Minting a new code for "the loader returned 500
    bytes" would put a number on the wire that no client knows how to read.

DESIGN DECISION — a prompt declares its arguments, and the declaration is the
whole contract.
    `prompts/get` is a call whose parameters are named in the declaration: a
    REQUIRED argument that is absent is -32602 naming it, an argument nobody
    declared is -32602, and an OPTIONAL argument that is absent is passed as
    absent so the builder keeps its own default. Quietly filling a missing
    argument with "" is the worst of the three: the builder cannot tell "the
    client meant empty" from "the client said nothing", and the prompt that comes
    out is plausible, wrong, and impossible to debug from the outside.

DESIGN DECISION — pagination belongs to the registry, not to the handler.
    Both registries take a `page`, mint their own cursors, and hand out the same
    pages for the same list: registration order, `page` entries, a `nextCursor`
    naming where the next page starts, and — on the last page — no `nextCursor`
    KEY at all. `{"nextCursor": null}` reads to a client as "there is a next page
    and I am not telling you where", which is how a paging loop lands back on
    page one forever. A cursor this registry never minted — not a number, or not
    a position in the CURRENT list — is -32602 with the cursor in `data`: the
    client should list again, not skip a page that has since moved.

TODO: implement

    PAGE = 2

    class Resource:
        __init__(self, uri, name, loader, *, mime_type="text/plain")
        .uri .name .loader .mime_type
        read() -> str                     # the text the client receives

    class Prompt:
        __init__(self, name, description, arguments, build)
        .name .description .arguments     # [{"name", "description"?, "required"?}]
        render(arguments) -> [{"role", "content": {"type": "text", "text"}}]

    class ResourceRegistry:
        __init__(self, *, page=PAGE)
        .resources -> dict[uri, Resource]       # registration order
        .add(resource) -> Resource
        .list_resources(params) -> {"resources": [{"uri", "name", "mimeType"}],
                                    "nextCursor"?}
        .read(params) -> {"contents": [{"uri", "mimeType", "text"}]}

    class PromptRegistry:
        __init__(self, *, page=PAGE)
        .prompts -> dict[name, Prompt]
        .add(prompt) -> Prompt
        .list_prompts(params) -> {"prompts": [{"name", "description",
                                               "arguments"}], "nextCursor"?}
        .get(params) -> {"description"?, "messages": [...]}

    install(server, resources, prompts) -> None      # the four methods above,
        registered with server.add(method, handler)
"""

PAGE = 0                            # TODO: the page size both registries default to


class Resource:
    def __init__(self, uri, name, loader, *, mime_type="text/plain"):
        raise NotImplementedError("stage 5: implement Resource()")

    def read(self):
        raise NotImplementedError("stage 5: implement Resource.read()")


class Prompt:
    def __init__(self, name, description, arguments, build):
        raise NotImplementedError("stage 5: implement Prompt()")

    def render(self, arguments):
        raise NotImplementedError("stage 5: implement Prompt.render()")


class ResourceRegistry:
    def __init__(self, *, page=PAGE):
        raise NotImplementedError("stage 5: implement ResourceRegistry()")

    def add(self, resource):
        raise NotImplementedError("stage 5: implement ResourceRegistry.add()")

    def list_resources(self, params):
        raise NotImplementedError("stage 5: implement ResourceRegistry.list_resources()")

    def read(self, params):
        raise NotImplementedError("stage 5: implement ResourceRegistry.read()")


class PromptRegistry:
    def __init__(self, *, page=PAGE):
        raise NotImplementedError("stage 5: implement PromptRegistry()")

    def add(self, prompt):
        raise NotImplementedError("stage 5: implement PromptRegistry.add()")

    def list_prompts(self, params):
        raise NotImplementedError("stage 5: implement PromptRegistry.list_prompts()")

    def get(self, params):
        raise NotImplementedError("stage 5: implement PromptRegistry.get()")


def install(server, resources, prompts):
    raise NotImplementedError("stage 5: implement install()")
