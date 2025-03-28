declare namespace JSX {
  interface IntrinsicElements {
    'custom-input': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & {
      value?: string;
      placeholder?: string;
      bindtextchange?: (e: { detail: { value: string } }) => void;
      bindfocus?: () => void;
      bindblur?: () => void;
    }, HTMLElement>;
    'input': React.DetailedHTMLProps<React.InputHTMLAttributes<HTMLInputElement> & {
      bindtextchange?: (e: { detail: { value: string } }) => void;
    }, HTMLInputElement>;
  }
} 