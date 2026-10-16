// LOCAL-ONLY: idempotent replica-set initiation for the slice stack (REL-0.1).
// Exits 0 when rs0 already exists or has been initiated and the node is primary.
function initiated() {
  try {
    return rs.status().ok === 1;
  } catch (error) {
    if (error.code === 94 || error.codeName === "NotYetInitialized") return false;
    throw error;
  }
}

if (initiated()) {
  print("rs0 already initiated");
} else {
  rs.initiate({ _id: "rs0", members: [{ _id: 0, host: "mongo:27017" }] });
  print("rs0 initiated");
}

for (let attempt = 0; attempt < 60; attempt += 1) {
  if (db.hello().isWritablePrimary) {
    print("primary ready");
    quit(0);
  }
  sleep(1000);
}
print("timed out waiting for the node to become primary");
quit(1);
