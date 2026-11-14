package main

import (
	"encoding/json"
	"errors"
)

type Product struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	PriceCents int    `json:"priceCents"`
	InStock    *bool  `json:"inStock"` // pointer, so a missing field is nil, not false
}

type ProductResponse struct {
	OK      bool     `json:"ok"`
	Product *Product `json:"product,omitempty"`
	Field   string   `json:"field,omitempty"`
}

func parseProduct(raw []byte) ProductResponse {
	var p Product
	// Decoding checks JSON types at runtime: "19.99" cannot go into an int.
	if err := json.Unmarshal(raw, &p); err != nil {
		var typeErr *json.UnmarshalTypeError
		if errors.As(err, &typeErr) {
			return ProductResponse{Field: typeErr.Field}
		}
		return ProductResponse{Field: "body"}
	}
	// Missing fields become zero values, so required rules are written by hand.
	switch {
	case p.ID == "":
		return ProductResponse{Field: "id"}
	case p.Name == "":
		return ProductResponse{Field: "name"}
	case p.PriceCents < 0:
		return ProductResponse{Field: "priceCents"}
	case p.InStock == nil:
		return ProductResponse{Field: "inStock"}
	}
	return ProductResponse{OK: true, Product: &p}
}
