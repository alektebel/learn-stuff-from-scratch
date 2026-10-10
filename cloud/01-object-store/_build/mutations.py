"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    ("delete_bucket wipes a non-empty bucket", "store.py",
     "        if any(versions for versions in bucket.objects.values()):\n"
     "            raise BucketNotEmpty(name)\n",
     "        bucket.objects.clear()\n",
     "4"),

    ("versioned delete removes the current version instead of adding a marker", "store.py",
     "            marker = Version(self._next_version_id(), b\"\", \"\", True, {})\n"
     "            bucket.objects.setdefault(key, []).append(marker)\n"
     "            return marker\n",
     "            if versions:\n"
     "                del bucket.objects[key]\n"
     "            return None\n",
     "2"),

    ("put is write-behind (eventually consistent)", "store.py",
     "        else:\n"
     "            bucket.objects[key] = [version]\n"
     "        return version\n",
     "        else:\n"
     "            pending = getattr(self, \"_deferred\", {})\n"
     "            pending[(bucket_name, key)] = version\n"
     "            self._deferred = pending\n"
     "        return version\n",
     "5"),

    ("list ignores the delimiter", "store.py",
     "            if delimiter:\n"
     "                rest = key[len(prefix):]\n",
     "            if False:\n"
     "                rest = key[len(prefix):]\n",
     "1"),

    ("ETag is not a content hash", "store.py",
     "        etag = hashlib.md5(data).hexdigest()\n",
     "        etag = \"0\" * 32\n",
     "3"),

    ("versioning enabled but each put still overwrites", "store.py",
     "            version.version_id = self._next_version_id()\n"
     "            bucket.objects.setdefault(key, []).append(version)\n",
     "            version.version_id = self._next_version_id()\n"
     "            bucket.objects[key] = [version]\n",
     "2"),

    ("verify accepts any signature", "presign.py",
     "    if not hmac.compare_digest(signature, expected):\n"
     "        raise InvalidSignatureError(\"signature does not match\")\n",
     "    if False:\n"
     "        raise InvalidSignatureError(\"signature does not match\")\n",
     "6"),

    ("verify never checks the expiry", "presign.py",
     "    if instant > int(expires_at):\n"
     "        raise ExpiredSignatureError(\n"
     "            \"token expired at %d (now %d)\" % (int(expires_at), instant)\n"
     "        )\n",
     "    if False:\n"
     "        raise ExpiredSignatureError(\n"
     "            \"token expired at %d (now %d)\" % (int(expires_at), instant)\n"
     "        )\n",
     "6"),
]
