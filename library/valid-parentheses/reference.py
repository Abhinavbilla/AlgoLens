def reference(s):
    # Keep deleting adjacent matching pairs; a valid string disappears completely.
    while "()" in s or "[]" in s:
        s = s.replace("()", "").replace("[]", "")
    return s == ""
