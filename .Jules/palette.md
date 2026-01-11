## 2025-02-12 - Accessible Tooltips Pattern
**Learning:** Tooltips implemented as `span:hover` are inaccessible. Keyboard users can't trigger them, and screen readers can't associate the trigger with the content.
**Action:** Use semantic `<button>` for triggers, link with `aria-describedby`, and use CSS `:focus-within` to show content on focus. Ensure button styles are reset to match design.
## 2024-05-23 - Accessible Tooltips
**Learning:** Tooltips using `group-hover` on `div`s are inaccessible to keyboard users. Using `react-tooltip` with a `button` trigger automatically handles focus management, ARIA attributes, and portal positioning, making it a robust solution for accessible tooltips.
**Action:** Always wrap tooltip triggers in interactive elements (like `button`) and use established libraries or patterns that handle focus and ARIA description linkage.
