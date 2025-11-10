module.exports = {
  echo: function(slots) {
    var txt = (slots && slots.text) ? slots.text : (typeof slots === 'string' ? slots : '');
    return { echoed: txt, ts: Date.now() };
  },
  on_start: function() { console.log('[echo] started'); },
  on_stop: function() { console.log('[echo] stopped'); }
};
