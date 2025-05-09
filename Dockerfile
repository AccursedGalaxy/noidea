FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application with version information
ARG VERSION=dev
ARG COMMIT=unknown
ARG BUILD_DATE=unknown

# Echo version info for debugging
RUN echo "Building version: ${VERSION}, commit: ${COMMIT}, date: ${BUILD_DATE}"

RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags "-X github.com/AccursedGalaxy/noidea/cmd.Version=${VERSION} -X github.com/AccursedGalaxy/noidea/cmd.BuildDate=${BUILD_DATE} -X github.com/AccursedGalaxy/noidea/cmd.Commit=${COMMIT}" \
    -o noidea

# Create a minimal image
FROM alpine:3.19

RUN apk add --no-cache git

WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/noidea /app/noidea

# Create config directory
RUN mkdir -p /root/.noidea

# Copy scripts
COPY scripts/ /app/scripts/
COPY personalities.toml.example /root/.noidea/personalities.toml

# Make scripts executable
RUN chmod +x /app/scripts/*.sh /app/scripts/prepare-commit-msg

# Add to PATH
ENV PATH="/app:${PATH}"

ENTRYPOINT ["/app/noidea"]
CMD ["--help"] 