import { all, create } from "mathjs"

export const math = create(all, {});
export const limitedEvaluate = math.evaluate;

math.import && math.import({
  'import':     function () { throw new Error('Function import is disabled') },
  'createUnit': function () { throw new Error('Function createUnit is disabled') },
//   'evaluate':   function () { throw new Error('Function evaluate is disabled') },
//   'parse':      function () { throw new Error('Function parse is disabled') },
  'simplify':   function () { throw new Error('Function simplify is disabled') },
  'derivative': function () { throw new Error('Function derivative is disabled') }
}, { override: true });
