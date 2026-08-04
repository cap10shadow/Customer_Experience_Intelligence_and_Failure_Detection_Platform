import '@testing-library/jest-dom/vitest'

// jsdom does not implement matchMedia; ThemeProvider and useMediaQuery both
// depend on it, so every test needs a working stub regardless of whether
// that specific test cares about media queries.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList
}
