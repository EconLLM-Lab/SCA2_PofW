// WB7-Q: what the public workbench does not ship, said plainly, in one place.
// The bundle builder ships a light run (the Ladder, Matrix and Cohort arrays) or only the index numbers
// for every comparator outside the featured pairs, and drops the per-head array from those pairs.
// Copy lives here, outside common.ts, so the two files never edit the same strings.

/** A full capture is what the 3D tab and a pinned head's attention draw. */
export const NO_3D =
  "The public workbench ships the full 3D capture only for the featured pairs. This comparator has the Ladder, Matrix and Cohort views.";
/** Numbers only: not even the Ladder and Matrix arrays of the comparator are in the sample. */
export const NO_3D_NUMBERS =
  "The public workbench ships the full 3D capture only for the featured pairs. This comparator has the Cohort view only.";
/** A pair of a new comparator ships without d_head_norm: the Matrix per-head panel has no bars to draw. */
export const NO_PER_HEAD = "Per-head detail ships only for the featured pairs.";
/** A comparator whose run arrays are not in the sample at all. */
export const NOT_IN_SAMPLE = "not shipped in the public sample";

/** One plain sentence, in the same card frame as the other panels. No spinner, no error panel. */
export const notShippedPanel = (sentence: string, title = "Not shipped in the public sample"): string =>
  `<section class="obj notshipped" data-obj="notshipped"><header><span class="cap">${title}</span></header><p>${sentence}</p></section>`;

/** A comparator whose run has no arrays at all (tier `numbers`): the Ladder, Matrix and 3D object have nothing to draw.
 * The sentence is HTML: "Cohort tab" links to the Cohort on the same question (data-go keeps the pair in the app). */
export const NUMBERS_ONLY = "The public workbench ships only this comparator's answer probabilities, not its internal data. You can see it in the Cohort tab.";
export const numbersOnlyHTML = (item: string): string => {
  const q = `item=${encodeURIComponent(item)}`;
  return NUMBERS_ONLY.replace("Cohort tab", `<a href="?tab=k&${q}" data-go="k" data-extra="${q}">Cohort tab</a>`);
};
/** The text beside a numbers-only comparator in a picker. */
export const COHORT_ONLY = "Cohort only";
