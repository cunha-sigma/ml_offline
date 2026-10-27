-- Turns ```mermaid code fences into <pre class="mermaid"> blocks so
-- mermaid.js (loaded in the HTML head) picks them up and renders them
-- in-browser before the page is printed to PDF.
local function escape_html(s)
  s = s:gsub("&", "&amp;")
  s = s:gsub("<", "&lt;")
  s = s:gsub(">", "&gt;")
  return s
end

function CodeBlock(el)
  if el.classes[1] == "mermaid" then
    return pandoc.RawBlock(
      "html",
      "<pre class=\"mermaid\">\n" .. escape_html(el.text) .. "\n</pre>"
    )
  end
end
