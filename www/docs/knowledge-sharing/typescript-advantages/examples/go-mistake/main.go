package main

import "fmt"

func main() {
	res := parseProduct([]byte(`{"id":"p1","name":"Mug","priceCents":1299,"inStock":true}`))
	// The same typo as the TypeScript example.
	fmt.Println(res.Product.PriceCent)
}
