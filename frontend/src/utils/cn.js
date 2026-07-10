/** Join truthy class names into a single string (tiny classnames helper). */
export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}
