function escapeRegExp(s) {
  const specials = "*+?^${}()|[]\\/.";
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    out += (specials.indexOf(ch) >= 0) ? String.fromCharCode(92) + ch : ch;
  }
  return out;
}
