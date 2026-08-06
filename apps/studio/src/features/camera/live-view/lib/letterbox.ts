interface BoxSize {
  height: number;
  width: number;
}

export interface ContainBox {
  height: number;
  left: number;
  top: number;
  width: number;
}

export function containScale(container: BoxSize, content: BoxSize): number {
  return Math.min(container.width / content.width, container.height / content.height);
}

export function fitContainBox(container: BoxSize, content: BoxSize): ContainBox {
  const scale = containScale(container, content);
  const width = content.width * scale;
  const height = content.height * scale;

  return {
    left: (container.width - width) / 2,
    top: (container.height - height) / 2,
    width,
    height,
  };
}
