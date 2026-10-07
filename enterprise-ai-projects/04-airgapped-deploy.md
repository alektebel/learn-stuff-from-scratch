# 4 — Air-gapped one-click deployer

## What it is

A package and a procedure that install your whole stack — services, models, database,
observability — into a Kubernetes cluster with no outbound internet, starting from a file
on removable media, finishing in under 30 minutes, with a human who has never seen your
software running the commands.

## What it actually demonstrates

That you have internalised the difference between "my deployment works" and "my
deployment works when nothing can be fetched". Almost every deployment fails in an air
gap for the same boring reason: something, somewhere, pulls from the network at install
time and nobody knew. Finding all of them is the project.

The 30-minute constraint is the interesting part, not the packaging. It forces you to
know your image sizes, your model weights, and your startup ordering, because 40 GB of
weights over USB 3 is a number you now have to care about.

## The substrate

**Zarf** (`zarf-dev/zarf`), the airgap-native package manager for Kubernetes. It exists
precisely for this: you declare images, Helm charts, manifests, scripts and binaries in a
`zarf.yaml`, build a single signed tarball on the connected side, carry it across, and
deploy with a statically compiled binary that has no dependencies.

Cluster: **k3s** (closest to what actually gets installed in customer VPCs) or **kind**
(faster iteration). Do the final run on k3s.

Make the gap real. Not "I did not use the internet" — actually cut it:

```bash
# run the deploy in a network namespace with no route out
sudo unshare --net --mount --pid --fork bash
# ... bring up only loopback, then deploy
```

If your deploy succeeds on a machine that *could* reach the internet, you have tested
nothing. The whole value of this project is in the failures, and you only see them when
the network genuinely is not there.

## The decisions

**Image bundling strategy.** Zarf can bundle images into the package and inject a
registry into the cluster. The alternative is to require the customer to have a registry
already and push into it. Bundling is one-click and produces a very large file; requiring
a registry is a smaller file and a prerequisite conversation with their platform team.
Which you choose says something about who your customer is.

**Model weights: in the package or separate.** Weights dominate the size. In-package
means one artefact and a 40 GB transfer for every patch release. Separate means two
things to keep in sync and a version-skew failure mode. If you have done
`compression-lower-bounds/compression/` on the other branch, this is where quantization
stops being an accuracy question and becomes a logistics one — 4 bits per weight is a
4× smaller USB stick and a 4× shorter transfer.

**Secrets.** There is no cloud KMS. No Secrets Manager, no IMDS, no OIDC federation.
Someone types something, or a file comes in on the media. Both are auditable badly.
Decide where the trust root is and write down who can see it.

**Certificates.** No Let's Encrypt: no ACME, no OCSP, no CRL fetch. Internal CA, or
self-signed with a documented trust-distribution step. Then find every client library in
your stack that does its own certificate validation with its own trust store — that list
is longer than you expect and each entry is a separate 20-minute debugging session at the
customer site.

**Time.** No public NTP. If the cluster's clock is wrong, certificate validation fails and
JWTs are rejected, and the error messages will not say "clock". Ask about their NTP source
before you go.

## Where it breaks

The upgrade. A first install into a clean cluster is the easy case, and it is the one
everybody demos. The second delivery has to reconcile with whatever state the customer's
cluster is in — including changes their platform team made, a half-failed previous
upgrade, and a CRD version you have since changed. You cannot fetch anything to help you
diagnose it and you are on a screen-share.

Build the second install before you polish the first.

## Resources

- Zarf documentation — <https://docs.zarf.dev/> `[v]`; source <https://github.com/zarf-dev/zarf> `[v]`
- Kubernetes blog, *Bootstrap an Air Gapped Cluster With Kubeadm* — <https://kubernetes.io/blog/2023/10/12/bootstrap-an-air-gapped-cluster-with-kubeadm/> `[v]`
- Helm documentation, chart dependencies and `helm package` — <https://helm.sh/docs/>
- `deploy-and-debug/` in this repo — liveness vs readiness, canary analysis, budget-based auto-rollback. The rollout half of this project is there.
- Sigstore / `cosign` — <https://docs.sigstore.dev/>. Signing matters more here than in a connected environment, because the customer cannot check anything against a live service.
