## 2025-02-12 - Accessible Tooltips Pattern
**Learning:** Tooltips implemented as `span:hover` are inaccessible. Keyboard users can't trigger them, and screen readers can't associate the trigger with the content.
**Action:** Use semantic `<button>` for triggers, link with `aria-describedby`, and use CSS `:focus-within` to show content on focus. Ensure button styles are reset to match design.
