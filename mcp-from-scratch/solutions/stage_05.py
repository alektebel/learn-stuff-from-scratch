"""MCP From Scratch — stage 5: resources, prompts, and the three ways a name is missing

SOLUTION. Two registries that resolve a name before they run anything: a URI that
is not registered never reaches a loader, an argument that was not declared never
reaches a builder, and a name that is missing gets the code that matches what was
looked up — -32002 for a resource URI, -32602 for anything passed to a method.
"""

from stage_01 import ERRORS, ProtocolError

PAGE = 2

ROLES = ("user", "assistant")


def _page_offset(params, total):
    """The offset a cursor names, for a list of `total` entries.

    A cursor is the `str(offset)` this registry itself handed out, so anything
    that is not a number, or not a position in the CURRENT list, is refused:
    a cursor from a page that has since changed would otherwise skip entries
    silently.
    """
    cursor = params.get("cursor")
    if cursor is None:
        return 0
    offset = None
    if isinstance(cursor, int) and not isinstance(cursor, bool):
        offset = cursor
    elif isinstance(cursor, str) and cursor.isascii() and cursor.isdigit():
        offset = int(cursor)
    if offset is None or not 0 <= offset < total:
        raise ProtocolError(
            ERRORS["invalid_params"],
            f"cursor {cursor!r} is not a position in this list of {total}: a "
            f"cursor is one the listing handed back, not one you write yourself",
            data={"cursor": cursor})
    return offset


def _messages(name, built):
    """The builder's output, validated and copied: a prompt renders messages."""
    if not isinstance(built, list):
        raise ValueError(
            f"the builder for {name!r} returned a {type(built).__name__}, and a "
            f"prompt renders a LIST of messages")
    messages = []
    for message in built:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError(
                f"the builder for {name!r} produced {message!r}: a message is "
                f"exactly {{'role', 'content'}} and nothing else")
        role = message["role"]
        if role not in ROLES:
            raise ValueError(
                f"the builder for {name!r} produced the role {role!r}, and a "
                f"prompt message is {' or '.join(ROLES)}")
        content = message["content"]
        if (not isinstance(content, dict) or content.get("type") != "text"
                or not isinstance(content.get("text"), str)):
            raise ValueError(
                f"the builder for {name!r} produced the content {content!r}: a "
                f"prompt message carries a text block "
                f'{{"type": "text", "text": str}}')
        messages.append({"role": role,
                         "content": {"type": "text", "text": content["text"]}})
    return messages


class Resource:
    def __init__(self, uri, name, loader, *, mime_type="text/plain"):
        if not isinstance(uri, str) or not uri:
            raise ValueError(
                "a resource needs a non-empty string uri: it is the address a "
                "client asks for it by")
        if not isinstance(name, str) or not name:
            raise ValueError(
                "a resource needs a non-empty string name: it is what the client "
                "shows a human")
        if not callable(loader):
            raise ValueError(
                "a resource needs a callable loader: without one there is nothing "
                "to read")
        self.uri = uri
        self.name = name
        self.loader = loader
        self.mime_type = mime_type

    def read(self):
        text = self.loader()
        if not isinstance(text, str):
            raise TypeError(
                f"{self.uri}: the loader returned a {type(text).__name__}, and a "
                f"resource is text (mimeType {self.mime_type!r})")
        return text


class Prompt:
    def __init__(self, name, description, arguments, build):
        if not isinstance(name, str) or not name:
            raise ValueError("a prompt needs a non-empty string name")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValueError(
                "a prompt's description is text, or None when it has none")
        if not callable(build):
            raise ValueError(
                "a prompt needs a callable builder: a declaration that cannot "
                "render is not a prompt")
        arguments = list(arguments)
        declared = set()
        for argument in arguments:
            if (not isinstance(argument, dict)
                    or not isinstance(argument.get("name"), str)
                    or not argument["name"]):
                raise ValueError(
                    f"a prompt argument is {{'name': str, ...}}, got {argument!r}")
            if argument["name"] in declared:
                raise ValueError(
                    f"the prompt {name!r} declares the argument "
                    f"{argument['name']!r} twice")
            declared.add(argument["name"])
        self.name = name
        self.description = description
        self.arguments = arguments
        self.build = build

    def render(self, arguments):
        if not isinstance(arguments, dict):
            raise ProtocolError(
                ERRORS["invalid_params"],
                f"prompts/get arguments for {self.name!r} must be an object, got "
                f"{type(arguments).__name__}")
        declared = {argument["name"]: argument for argument in self.arguments}
        for name in arguments:
            if name not in declared:
                raise ProtocolError(
                    ERRORS["invalid_params"],
                    f"the prompt {self.name!r} declares no argument {name!r}")
        values = {}
        for name, argument in declared.items():
            if name in arguments:
                values[name] = arguments[name]
            elif argument.get("required"):
                raise ProtocolError(
                    ERRORS["invalid_params"],
                    f"the prompt {self.name!r} requires the argument {name!r}")
        return _messages(self.name, self.build(values))


class ResourceRegistry:
    def __init__(self, *, page=PAGE):
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError("page is a positive integer: it is how many entries "
                             "a listing hands out at a time")
        self.page = page
        self.resources = {}

    def add(self, resource):
        self.resources[resource.uri] = resource
        return resource

    def list_resources(self, params):
        offset = _page_offset(params, len(self.resources))
        window = list(self.resources.values())[offset:offset + self.page]
        result = {"resources": [{"uri": r.uri, "name": r.name,
                                 "mimeType": r.mime_type} for r in window]}
        if offset + self.page < len(self.resources):
            result["nextCursor"] = str(offset + self.page)
        return result

    def read(self, params):
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri:
            raise ProtocolError(
                ERRORS["invalid_params"],
                "resources/read takes the uri of a registered resource")
        resource = self.resources.get(uri)
        if resource is None:
            raise ProtocolError(ERRORS["resource_not_found"], "Resource not found",
                                data={"uri": uri})
        return {"contents": [{"uri": resource.uri,
                              "mimeType": resource.mime_type,
                              "text": resource.read()}]}


class PromptRegistry:
    def __init__(self, *, page=PAGE):
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError("page is a positive integer: it is how many entries "
                             "a listing hands out at a time")
        self.page = page
        self.prompts = {}

    def add(self, prompt):
        self.prompts[prompt.name] = prompt
        return prompt

    def list_prompts(self, params):
        offset = _page_offset(params, len(self.prompts))
        window = list(self.prompts.values())[offset:offset + self.page]
        result = {"prompts": [{"name": p.name, "description": p.description,
                               "arguments": [dict(a) for a in p.arguments]}
                              for p in window]}
        if offset + self.page < len(self.prompts):
            result["nextCursor"] = str(offset + self.page)
        return result

    def get(self, params):
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise ProtocolError(
                ERRORS["invalid_params"],
                "prompts/get takes the name of a prompt the server declares")
        prompt = self.prompts.get(name)
        if prompt is None:
            raise ProtocolError(ERRORS["invalid_params"], f"unknown prompt {name!r}",
                                data={"name": name})
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        result = {"messages": prompt.render(arguments)}
        if prompt.description:
            result["description"] = prompt.description
        return result


def install(server, resources, prompts):
    server.add("resources/list",
               lambda params, session: resources.list_resources(params))
    server.add("resources/read",
               lambda params, session: resources.read(params))
    server.add("prompts/list",
               lambda params, session: prompts.list_prompts(params))
    server.add("prompts/get",
               lambda params, session: prompts.get(params))
