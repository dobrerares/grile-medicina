import { useState } from "react";

export default function ComplementGrupatInfo() {
  const [open, setOpen] = useState(false);

  return (
    <div className="cg-info">
      <button
        className="cg-info-toggle"
        type="button"
        onClick={() => setOpen(!open)}
      >
        {open ? "Ascunde" : "Afiseaza"} legenda Complement Grupat
      </button>
      {open && (
        <div className="cg-info-table">
          <table>
            <thead>
              <tr>
                <th>Raspuns</th>
                <th>Afirmatii corecte</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>A</td>
                <td>1, 2, 3</td>
              </tr>
              <tr>
                <td>B</td>
                <td>1, 3</td>
              </tr>
              <tr>
                <td>C</td>
                <td>2, 4</td>
              </tr>
              <tr>
                <td>D</td>
                <td>numai 4</td>
              </tr>
              <tr>
                <td>E</td>
                <td>toate (1, 2, 3, 4)</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
