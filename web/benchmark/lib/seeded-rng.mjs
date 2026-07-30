export function createSeededRng(seed) {
  let state = seed >>> 0;

  function random() {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  }

  return {
    random,
    int(min, max) {
      return Math.floor(random() * (max - min + 1)) + min;
    },
    pick(items) {
      return items[this.int(0, items.length - 1)];
    },
  };
}
