/** Fix legacy singular-type strings stored as "Observations ['x']". */
export function normalizeObservationGrammar(reasoning: string): string {
  return reasoning.replace(
    /^\s*Observations (\[\s*'[^']+'\s*\])/,
    "Observation $1"
  );
}
