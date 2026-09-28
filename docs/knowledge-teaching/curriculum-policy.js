/** Optional instructor exercise: change only this 5–10 line ordering policy.
 * Input: student | lawyer. Output: unique learning-path IDs.
 * TODO(instructor): choose whether practising lawyers start with foundations
 * or use foundations as a prerequisite checklist before contract drafting.
 * The default below is complete and deliberately foundation-first.
 */
export function preferredPaths(audience) {
  return audience === 'lawyer'
    ? ['foundation', 'drafting', 'corporate', 'risk', 'growth']
    : ['foundation', 'corporate', 'risk', 'drafting', 'growth'];
}
