# 9 — Automated compliance auditor

## What it is

Something that runs continuously against a deployment, checks it against a named set of
security controls, and produces a report a customer's security team will accept as
evidence.

## What it actually demonstrates

That you treat security as code — correct — and, more usefully, that you know the
difference between **a control** and **a check**. A control is a requirement from a
framework ("logical access is reviewed periodically"). A check is a testable assertion
about your system ("no IAM user has had a password unused for 90 days"). One control maps
to several checks, some controls map to no automatable check at all, and pretending
otherwise is how automated compliance tools lose credibility with auditors.

The valuable artefact is the **mapping**: control → checks → evidence → what is still
manual. Not the scanner.

## The substrate

Do not invent controls. Use published ones with real identifiers:

- **kube-bench** — CIS Kubernetes Benchmark, control by control, with the benchmark's own
  numbering. Aqua Security's, and the standard answer for cluster hardening.
- **Conftest** (built on **Open Policy Agent**) — write your own policies in Rego against
  Kubernetes manifests, Terraform plans, Dockerfiles. This is the "compliance as code"
  half; kube-bench is the "scan the running thing" half.
- **Prowler** — cloud posture, with mappings to CIS, NIST 800-53, NIST CSF, PCI-DSS,
  GDPR, HIPAA, SOC 2, FedRAMP and others already written. Read its mapping files even if
  you do not use the tool; they show you what "SOC 2 evidence" actually looks like in
  practice.
- **Trivy** — vulnerabilities and misconfiguration, for the image half.

Then build the thing none of them are: the aggregator that takes their output, maps it to
one framework, and produces a readiness report with a date and a scope.

## The decisions

**Which framework you target, and admit you targeted one.** SOC 2 Type II, ISO 27001,
HIPAA Security Rule, and CIS are not interchangeable. A report that says "compliant"
without naming a framework and a scope is worthless, and an auditor will say so in the
first meeting.

**Point-in-time or continuous.** A scan is evidence about a moment. SOC 2 Type II is about
a *period* — the auditor wants evidence the control operated throughout. That means
retaining every scan result, with timestamps, immutably, which is a storage and integrity
problem rather than a scanning one. This distinction is the single most common thing
missed in projects like this.

**Failing open in the pipeline.** If your auditor blocks deploys on any finding, someone
will disable it within a month. If it blocks nothing, it is a dashboard. The workable
position is a severity gate plus a time-boxed exception mechanism with an owner and an
expiry — and the exceptions register is then itself audit evidence.

**False positives cost more than false negatives here.** A checker that flags compliant
configurations trains its users to ignore it, after which it detects nothing. Tune for
precision and state your recall.

## Where it breaks

The control that cannot be automated. "Management reviews access quarterly." "Personnel
receive security training." "There is a documented incident response plan and it is
tested." No scanner reaches any of these, and they are a large fraction of any real
framework.

Your report has to distinguish three states, not two: **passing**, **failing**, and
**not assessable by this tool**. A report that silently omits the third category
overstates readiness, and that is the failure mode that gets noticed in the audit rather
than by you.

## Resources

- kube-bench — <https://github.com/aquasecurity/kube-bench> `[v]`
- Open Policy Agent and Conftest — <https://www.openpolicyagent.org/>, <https://www.openpolicyagent.org/ecosystem/entry/conftest> `[v]`
- Prowler — <https://github.com/prowler-cloud/prowler> `[v]` — its compliance framework mappings are the most useful part for this project
- Trivy — <https://github.com/aquasecurity/trivy>
- CIS Benchmarks — <https://www.cisecurity.org/cis-benchmarks>
- AICPA Trust Services Criteria (the actual source for SOC 2) — read the criteria themselves once; they are shorter and vaguer than you expect, and that vagueness is why the mapping is the work.
- NIST SP 800-53 Rev. 5 control catalogue, and OSCAL (<https://pages.nist.gov/OSCAL/>) if you want a machine-readable format for the mapping rather than inventing one.
