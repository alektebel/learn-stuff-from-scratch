# 7 — Enterprise SSO & SCIM bridge

## What it is

Your application accepting SAML or OIDC single sign-on from a customer's identity
provider, plus a SCIM 2.0 endpoint that lets that IdP create, update, deactivate and
group users in your system automatically.

## What it actually demonstrates

That you can pass an enterprise IT review — which is the correct claim, and one of the few
in the list that is not overstated. The reason it works as a signal is that SSO and SCIM
are *specified*: there are RFCs, there are conformance expectations, and either your
`/Users` endpoint behaves as the spec says or the customer's IdP breaks in a way that is
your fault.

## The substrate

**Keycloak.** It speaks SAML 2.0 and OIDC natively and you can run it in a container, so
you get a real IdP without an Okta contract.

One accuracy note, because it changes your plan: **Keycloak's SCIM support is not the same
maturity as its SSO support.** As of 26.6 there is a native SCIM 2.0 server as a *preview*
feature behind a flag, covering core user and group operations rather than the full
protocol surface; before that, and still commonly, people use community extensions
(`Metatavu/keycloak-scim-server` for the server side, `mitodl/keycloak-scim` for the
client side). Verify the state of this against the Keycloak release notes when you start —
it is moving.

Because of that, the sharper way to build this project is to invert it: **you** implement
the SCIM *server* (that is what a SaaS vendor does — the IdP provisions into you), and use
Keycloak, or a SCIM client/test harness, as the thing driving it. Then the specification
is yours to satisfy, which is the actual job.

For SSO testing, `samltest.id` and Keycloak's own OIDC endpoints both work.

## The decisions

**SAML or OIDC.** OIDC is JSON, has better libraries, and is what you would choose. Large
enterprises frequently mandate SAML because that is what their existing federation does.
Supporting both doubles your surface; supporting only OIDC loses deals. Say which you
chose and why, because "SAML is legacy" is not an answer that survives a procurement
conversation.

**Just-in-time provisioning or SCIM.** JIT creates the user on first login and is one
afternoon of work. It cannot deprovision — a terminated employee keeps their account until
someone notices, which is precisely the finding that fails a security review. SCIM
deprovisions, and costs you a specified REST API with `PATCH` semantics you do not get to
simplify.

**SCIM `PATCH` is the hard part and it is where implementations fail.** RFC 7644 defines
a patch operation with a path syntax and `add`/`remove`/`replace` semantics over
multi-valued attributes. Azure AD and Okta emit different but individually legal patch
documents. Implementing `PATCH` as "replace the whole user" passes your tests and fails
against a real IdP. Read §3.5.2 of RFC 7644 properly and write tests from the examples in
it.

**Deactivate or delete.** SCIM's `active: false` means deactivate. Most IdPs never send
`DELETE`. If your handler treats deactivation as deletion you destroy the user's data on
a temporary suspension; if you ignore `active: false` you have not deprovisioned anyone.

**Role and group mapping.** The IdP sends group names. Your app has roles. That mapping is
per-customer configuration, it changes, and it is the single most common source of
"why can this user see that" tickets. Design where it lives before you need it.

## Where it breaks

A user is renamed and their email changes. Your join key was the email. Now the IdP sends
a `PATCH` for a user you cannot find, or you create a duplicate.

The `externalId` attribute exists for exactly this reason and it is the field everyone
ignores until this happens. Key on the IdP's immutable identifier from the first line of
code.

## Resources

- RFC 7642 — SCIM: definitions, overview, concepts, requirements — <https://www.rfc-editor.org/rfc/rfc7642.html> `[v]`
- RFC 7643 — SCIM: core schema `[v]`
- RFC 7644 — SCIM: protocol (September 2015) `[v]` — §3.5.2 (`PATCH`) is the section that decides whether this works
- Keycloak — <https://www.keycloak.org/>; extensions index <https://www.keycloak.org/extensions> `[v]`
- SAML 2.0 core and bindings, OASIS — and OpenID Connect Core 1.0, <https://openid.net/specs/openid-connect-core-1_0.html>
- Okta and Microsoft Entra both publish their SCIM client expectations; read both, because the differences between them are the compatibility work.
