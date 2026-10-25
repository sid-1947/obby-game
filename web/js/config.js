export const COURSE = Object.freeze({
  platformCount: 36,
  spacing: 8.8,
  platformLength: 6.2,
  platformWidth: 7.2,
  gravity: 31,
  jumpSpeed: 16,
  moveSpeed: 9.5,
  maxHealth: 3,
  checkpointInterval: 6,
});

export const AVATARS = Object.freeze([
  { id: "mint", name: "Mint", coat: "#54d9b0", trim: "#e4fff4", hair: "#342a4b", skin: "#f3c5a2", price: 0, mark: "✦" },
  { id: "coral", name: "Coral", coat: "#ff7f85", trim: "#ffe4c9", hair: "#503241", skin: "#e6ae8c", price: 8, mark: "✿" },
  { id: "violet", name: "Violet", coat: "#a88dff", trim: "#ece5ff", hair: "#29284d", skin: "#e9bd9c", price: 16, mark: "✧" },
  { id: "sunny", name: "Sunny", coat: "#ffc857", trim: "#fff2bc", hair: "#764a2c", skin: "#f1c8a2", price: 24, mark: "☼" },
  { id: "berry", name: "Berry", coat: "#ed78c1", trim: "#ffe4f4", hair: "#352440", skin: "#c98f78", price: 32, mark: "♥" },
]);

export const COLORS = Object.freeze({
  skyTop: "#7bc9ed",
  skyBottom: "#eaf8ff",
  mountainFar: "#acd9e5",
  mountainNear: "#79c4cf",
  platform: "#63d4ae",
  checkpoint: "#8a8cff",
  moving: "#ffbc62",
});
