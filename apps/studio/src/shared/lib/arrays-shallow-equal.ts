export function arraysShallowEqual<T>(left: readonly T[], right: readonly T[]): boolean {
  return (
    left.length === right.length &&
    left.every((item, index) => {
      return item === right[index];
    })
  );
}
