package main

import (
	"errors"
	"fmt"

	"github.com/go-playground/validator/v10"
)

var validate *validator.Validate

func init() {
	validate = validator.New()
}

func ValidateStruct(s interface{}) error {
	err := validate.Struct(s)
	if err != nil {
		var errs []string
		for _, e := range err.(validator.ValidationErrors) {
			errs = append(errs, fmt.Sprintf("%s is required", e.Field()))
		}
		return errors.New(joinString(errs))
	}
	return nil
}

func joinString(s []string) string {
	if len(s) == 0 {
		return ""
	}
	return s[0]
}
