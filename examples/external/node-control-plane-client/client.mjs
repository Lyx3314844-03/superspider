const args = process.argv.slice(2);

function getFlag(name) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : "";
}

const base = getFlag("--base");
const url = getFlag("--url");

if (!base || !url) {
  console.error("Usage: node client.mjs --base <api/tasks> --url <target>");
  process.exit(1);
}

const response = await fetch(base, {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({name: "node-client-demo", url}),
});

const payload = await response.json();
console.log(JSON.stringify(payload, null, 2));
