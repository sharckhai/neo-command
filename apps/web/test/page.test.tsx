import { render } from "@testing-library/react";
import Home from "../app/page";

test("renders chat input", () => {
  const { getByPlaceholderText } = render(<Home />);
  getByPlaceholderText(/ask/i);
});
