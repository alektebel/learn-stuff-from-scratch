"""Deliberately break the solutions and confirm the checker notices."""
import pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-01" / "aws-from-scratch"

BUGS = [
 (2, "iam.py", "resource matching folds case, so a policy grants more than it says",
  '    return fnmatch.fnmatch(resource, pattern)',
  '    return fnmatch.fnmatch(resource.lower(), pattern.lower())'),
 (2, "iam.py", "Bool coerces the policy value, inverting the condition",
  '        return any(bool(actual) == (str(option).lower() == "true")\n                   for option in options)',
  '        return any(bool(actual) == bool(option) for option in options)'),

 # ---- capstone.py ------------------------------------------------------
 (18, "capstone.py", "authorisation happens after the side effects, not before",
  '''    cloud.authorize(credentials, "s3:PutObject", f"arn:aws:s3:::uploads/{key}")
    cloud.authorize(credentials, "kms:GenerateDataKey",
                    "arn:aws:kms:::alias/uploads")

    ciphertext, wrapped = cipher.encrypt(body, {"tenant": tenant})
    cloud.s3.put_object("uploads", key, ciphertext,
                        metadata={"kms_version": str(wrapped.version)})''',
  '''    ciphertext, wrapped = cipher.encrypt(body, {"tenant": tenant})
    cloud.s3.put_object("uploads", key, ciphertext,
                        metadata={"kms_version": str(wrapped.version)})

    cloud.authorize(credentials, "s3:PutObject", f"arn:aws:s3:::uploads/{key}")
    cloud.authorize(credentials, "kms:GenerateDataKey",
                    "arn:aws:kms:::alias/uploads")'''),
 (18, "capstone.py", "the payload is stored in the clear",
  '''    ciphertext, wrapped = cipher.encrypt(body, {"tenant": tenant})
    cloud.s3.put_object("uploads", key, ciphertext,''',
  '''    ciphertext, wrapped = cipher.encrypt(body, {"tenant": tenant})
    cloud.s3.put_object("uploads", key, body,'''),
 (18, "capstone.py", "a failed message is deleted from the queue anyway",
  '        try:\n            result = cloud.lambda_service.invoke("indexer", event, now=now)',
  '        queue.delete(message.receipt_handle)\n        try:\n            result = cloud.lambda_service.invoke("indexer", event, now=now)'),

 # ---- sns.py -----------------------------------------------------------
 (12, "sns.py", "the filter policy is never consulted, so every subscriber gets everything",
  '            if not matches_filter(subscription.filter_policy, attributes):',
  '            if False:'),
 (12, "sns.py", "filter keys OR instead of AND",
  '''        if key not in attributes:
            return False               # missing attribute never matches''',
  '''        if key not in attributes:
            continue                   # missing attribute never matches'''),
 (12, "sns.py", "an absent attribute satisfies an exists:false rule and vice versa",
  '''            if (key in attributes) != wanted:
                return False''',
  '''            if (key in attributes) == wanted:
                return False'''),
 # ---- kms.py -----------------------------------------------------------
 (14, "kms.py", "the data key is stored unwrapped, so the envelope protects nothing",
  '                                        _xor(plaintext, wrapping), dict(context)))',
  '                                        plaintext, dict(context)))'),
 (15, "kms.py", "the encryption context is not checked on decrypt",
  '''        if context != encrypted.context:
            raise KMSError(''',
  '''        if False:
            raise KMSError('''),
 (15, "kms.py", "rotation replaces old key material instead of appending",
  '''        self.versions.append(KeyVersion(len(self.versions) + 1,
                                        secrets.token_bytes(32)))''',
  '''        self.versions[:] = [KeyVersion(len(self.versions) + 1,
                                       secrets.token_bytes(32))]'''),
 # ---- vpc.py -----------------------------------------------------------
 (16, "vpc.py", "routing takes the first match, not the longest prefix",
  '''            if network.contains_ip(address) and network.network.prefixlen > best_length:
                best, best_length = target, network.network.prefixlen''',
  '''            if network.contains_ip(address):
                return target'''),
 (17, "vpc.py", "the NACL reply is evaluated on the service port, not an ephemeral one",
  '        ok, why = acl.evaluate("out", protocol, ephemeral_port, source_ip)',
  '        ok, why = acl.evaluate("out", protocol, port, source_ip)'),
 (17, "vpc.py", "the NACL is not evaluated on the return path",
  '''    if acl is not None:
        ok, why = acl.evaluate("out", protocol, ephemeral_port, source_ip)''',
  '''    if False:
        ok, why = acl.evaluate("out", protocol, ephemeral_port, source_ip)'''),

 # ---- sqs.py -----------------------------------------------------------
 (6, "sqs.py", "receive deletes instead of leasing",
  '''            message.visible_at = now + self.visibility_timeout
            self.messages.remove(message)
            self.in_flight[handle] = message''',
  '''            message.visible_at = now + self.visibility_timeout
            self.messages.remove(message)'''),
 (6, "sqs.py", "an in-flight message is visible again immediately",
  '            message.visible_at = now + self.visibility_timeout',
  '            message.visible_at = now'),
 (6, "sqs.py", "receive_count is never incremented, so redelivery is invisible",
  '            message.receive_count += 1',
  '            pass'),
 (7, "sqs.py", "the poison pill is retried forever",
  '            if message.receive_count > self.max_receives:',
  '            if False and message.receive_count > self.max_receives:'),
 (7, "sqs.py", "FIFO hands out two messages from the same group at once",
  '''            if self.fifo and message.group_id in blocked_groups:
                continue''',
  '            if False:\n                continue'),
 # ---- dynamodb.py ------------------------------------------------------
 (8, "dynamodb.py", "a conditional write ignores its condition",
  '''        if condition is not None and not condition(existing):
            raise ConditionalCheckFailed(''',
  '''        if False:
            raise ConditionalCheckFailed('''),
 (8, "dynamodb.py", "query returns the whole table, not one partition",
  '            if pk == partition_value',
  '            if True'),
 (9, "dynamodb.py", "capacity is accounted per TABLE, not per partition",
  '            if self.write_used + units > self.write_capacity:',
  '            if False:'),
 (9, "dynamodb.py", "a scan is billed on items RETURNED, not items read",
  '        self.stats["scanned_items"] += scanned',
  '        self.stats["scanned_items"] += len(results)'),
 (9, "dynamodb.py", "a consistent read costs the same as an eventual one",
  '            partition.consume(1.0 if consistent else 0.5, "read", now)',
  '            partition.consume(0.5, "read", now)'),
 # ---- lambda_svc.py ----------------------------------------------------
 (10, "lambda_svc.py", "every invocation is a cold start",
  '        environment, cold = self._acquire_environment(function, now)',
  '        environment, cold = self._acquire_environment(function, now)\n        cold = True'),
 (10, "lambda_svc.py", "the init cost is never added to the first invocation",
  '            wall = duration_ms + (environment.init_ms if cold else 0.0)',
  '            wall = duration_ms'),
 (11, "lambda_svc.py", "reserved concurrency is a floor but not a ceiling",
  '''        if function.reserved_concurrency is not None:
            return function.reserved_concurrency - function.busy''',
  '''        if function.reserved_concurrency is not None:
            return self.account_concurrency - function.busy'''),
 (11, "lambda_svc.py", "a reservation does not reduce the unreserved pool",
  '''        reserved = sum(f.reserved_concurrency or 0
                       for f in self.functions.values())
        return self.account_concurrency - reserved''',
  '        return self.account_concurrency'),
 (11, "lambda_svc.py", "a timed-out invocation is billed for its actual duration",
  '                function.stats["billed_ms"] += function.timeout_s * 1000',
  '                function.stats["billed_ms"] += wall'),

 # ---- iam.py -----------------------------------------------------------
 (1, "iam.py", "an explicit Deny no longer wins",
  """            if statement.effect == DENY:
                return Decision(False, f"explicit Deny in {policy.name or 'policy'}"
                                       f"{' (' + statement.sid + ')' if statement.sid else ''}",
                                statement)""",
  """            if statement.effect == DENY:
                continue"""),
 (1, "iam.py", "no matching statement means allow",
  '    return Decision(False, "implicit Deny — no statement allows this")',
  '    return Decision(True, "implicit Deny — no statement allows this")'),
 (2, "iam.py", "conditions OR across keys instead of AND",
  """            if not _condition_holds(operator, actual, options):
                return False
    return True""",
  """            if _condition_holds(operator, actual, options):
                return True
    return not condition"""),
 (2, "iam.py", "a missing context key satisfies the condition",
  """    if actual is None:
        return False                      # a missing context key never matches""",
  """    if actual is None:
        return True                       # a missing context key never matches"""),
 (2, "iam.py", "the boundary grants on its own instead of capping",
  """    identity_decision = evaluate(identity, action, resource, context)
    if not identity_decision.allowed:
        return identity_decision""",
  """    identity_decision = evaluate(identity, action, resource, context)
    if not identity_decision.allowed and boundary is not None:
        return evaluate([boundary], action, resource, context)
    if not identity_decision.allowed:
        return identity_decision"""),
 (3, "iam.py", "assume-role checks the trust policy but not the caller's",
  """    permitted = evaluate(caller.policies, "sts:AssumeRole", role.arn, context)
    if not permitted.allowed:
        raise PermissionError(f"{caller.principal} lacks sts:AssumeRole on "
                              f"{role.arn}: {permitted.reason}")""",
  """    permitted = evaluate(caller.policies, "sts:AssumeRole", role.arn, context)"""),
 (3, "iam.py", "the session keeps the caller's permissions, not the role's",
  "    return Credentials(role.arn, role.permissions, session_name)",
  "    return Credentials(role.arn, caller.policies, session_name)"),
 # ---- s3.py ------------------------------------------------------------
 (4, "s3.py", "a multipart ETag is the MD5 of the whole body",
  '    digests = b"".join(hashlib.md5(part).digest() for part in parts)\n'
  '    return f"{hashlib.md5(digests).hexdigest()}-{len(parts)}"',
  '    return f"{hashlib.md5(body).hexdigest()}-{len(parts)}"'),
 (4, "s3.py", "the multipart ETag omits the part count",
  '    return f"{hashlib.md5(digests).hexdigest()}-{len(parts)}"',
  '    return hashlib.md5(digests).hexdigest()'),
 (5, "s3.py", "a delete marker still shows up in a listing",
  """        live = sorted(key for key, history in b.objects.items()
                      if history and not history[-1].is_delete_marker
                      and key.startswith(prefix))""",
  """        live = sorted(key for key, history in b.objects.items()
                      if history and key.startswith(prefix))"""),
 (5, "s3.py", "the delimiter is ignored, so no common prefixes are formed",
  """            if delimiter:
                rest = key[len(prefix):]
                if delimiter in rest:""",
  """            if delimiter and False:
                rest = key[len(prefix):]
                if delimiter in rest:"""),
 (5, "s3.py", "a plain delete on a versioned bucket really removes the bytes",
  """        marker = Version(b._next_version(), None, "", 0, time.time(), {})
        history.append(marker)
        return marker.version_id""",
  """        del b.objects[key]
        return None"""),

    (19, "pricing.py", "tiered_cost prices the whole volume at one rate",
     '''    remaining = float(quantity)
    previous = 0.0
    total = 0.0
    for upper, unit_price in tiers:
        if remaining <= 0:
            break
        span = min(remaining, upper - previous)
        total += span * unit_price
        remaining -= span
        previous = upper
    return total''',
     '''    rate = tiers[-1][1]
    for upper, unit_price in tiers:
        if quantity <= upper:
            rate = unit_price
            break
    return quantity * rate'''),

    (19, "pricing.py", "billable_units rounds instead of ceiling",
     "    return max(minimum_units, math.ceil(quantity / unit_size - 1e-9))",
     "    return max(minimum_units, round(quantity / unit_size))"),

    (20, "pricing.py", "scaled() multiplies the fixed lines too",
     '''            if _is_fixed(item):
                out.items.append(item)
            else:
                out.items.append(item._replace(''',
     '''            if False:
                out.items.append(item)
            else:
                out.items.append(item._replace('''),

    (20, "pricing.py", "money() rounds sub-cent line items to $0.00",
     '''    if amount == 0:
        return "$0"
    if abs(amount) >= 0.01:
        return f"${amount:,.2f}"
    return f"${amount:.6f}"''',
     '''    if amount == 0:
        return "$0"
    return f"${amount:,.2f}"'''),

    (21, "billing.py", "stored_bytes counts only the visible version",
     '''                elif version is current:
                    live += version.size
                else:
                    noncurrent += version.size''',
     '''                elif version is current:
                    live += version.size'''),

    (21, "billing.py", "bill_s3 ignores the minimum billable object size",
     "                kb = max(version.size / 1024.0, min_object_kb)",
     "                kb = version.size / 1024.0"),

    (22, "billing.py", "on-demand reads billed on items RETURNED",
     '''    read_units = table.stats["scanned_items"] * billable_units(
        avg_item_kb, 4.0) * (1.0 if consistent_reads else 0.5)''',
     '''    read_units = table.stats["returned_items"] * billable_units(
        avg_item_kb, 4.0) * (1.0 if consistent_reads else 0.5)'''),

    (22, "billing.py", "GB-seconds uses 1000 MB per GB",
     "    gb = function.memory_mb / 1024.0",
     "    gb = function.memory_mb / 1000.0"),

    (22, "billing.py", "idle polls folded into the work request line",
     '''        bill.add("sqs", "idle-poll-requests", empty_receives, "request",''',
     '''        bill.add("sqs", "requests", empty_receives, "request",'''),

    (22, "billing.py", "cross-AZ billed on one side only",
     '''        bill.add("network", "cross-az-gb", cross_az_gb * 2, "GB",''',
     '''        bill.add("network", "cross-az-gb", cross_az_gb, "GB",'''),

    (23, "optimize.py", "the crossover recalled instead of derived",
     "    return hourly / (3600.0 * on_demand)",
     "    return 0.15"),

    (23, "optimize.py", "the I/O wait scales with memory too",
     "    return io_wait_ms + cpu_work_ms_at_1_vcpu / max(vcpu, 1e-9)",
     "    return (io_wait_ms + cpu_work_ms_at_1_vcpu) / max(vcpu, 1e-9)"),

    (24, "optimize.py", "rank_savings groups by dimension, not service/dimension",
     '''        key = f"{item.service}/{item.dimension}"
        by_line[key] = by_line.get(key, 0.0) + item.cost''',
     '''        key = item.dimension
        by_line[key] = by_line.get(key, 0.0) + item.cost
    by_line.update({f"{i.service}/{i.dimension}": by_line[i.dimension]
                    for i in bill.items})'''),
]

failures = []
for step, filename, label, old, new in BUGS:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "s"
        shutil.copytree(ROOT / "solutions", work,
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "check.py", work / "check.py")
        target = work / filename
        text = target.read_text()
        if old not in text:
            failures.append(f"[{step}] {label}: PATCH DID NOT APPLY")
            continue
        target.write_text(text.replace(old, new, 1))
        result = subprocess.run([sys.executable, "check.py", str(step)],
                                cwd=work, capture_output=True, text=True)
        caught = "✗" in result.stdout
        mark = "caught" if caught else "MISSED"
        print(f"  step {step:>2}  {mark:<7} {label}")
        if not caught:
            failures.append(f"[{step}] {label}\n{result.stdout}")

print()
if failures:
    print("PROBLEMS:")
    for f in failures:
        print(" ", f)
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
