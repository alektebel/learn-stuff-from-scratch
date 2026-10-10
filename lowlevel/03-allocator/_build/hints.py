"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "allocator.py": {
  "HeapAllocator._find_first_fit": "Walk blocks from offset 16: read each tag, and return the first block that is BOTH free and at least `need` bytes. Step forward by that block's size; the epilogue tag stops you.",
  "HeapAllocator.malloc": "Round the request up to a 16-byte block (16+16 bytes of tags), find the first fit, and if the leftover is at least _MIN_BLOCK split it into a free block. Return block_start+16, or None.",
  "HeapAllocator.free": "None is a no-op. Reject a non-aligned or out-of-range pointer, and raise DoubleFree if the header's allocated bit is already clear. Then clear the bit, and merge with the NEXT block if its header says free and with the PREVIOUS block found through the footer just before this one.",
  "HeapAllocator.blocks": "Walk from offset 16, reading (size, allocated) at each block start; stop at the epilogue. Append Block(offset, size, offset+16, size-32, allocated) and check the sizes still tile the arena.",
  "HeapAllocator.utilization": "Sum the payload capacity of every allocated block (size - 32) and divide by arena_size.",
 },
}
