// Librerías estándar
#include <iostream>
#include <fstream>
#include <ctime>
#include <arpa/inet.h>      // Para funciones de red (htonl, socket, etc.)
#include <unistd.h>         // Para funciones de sistema como close()
#include <cstring>
#include <thread>           // Para sleep_for()
#include <chrono>
#include <random>           // Para generar números aleatorios

// Librerías de OpenSSL para cifrado y firma digital
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/sha.h>
#include <openssl/evp.h>

// Puerto TCP y dirección del servidor
#define PORT 8080
#define SERVER_ADDR "127.0.0.1"

// Convierte un entero de 64 bits a big-endian
uint64_t htonll(uint64_t value) {
    return ((uint64_t)htonl(value & 0xFFFFFFFF) << 32) | htonl(value >> 32);
}

// Convierte un float a entero de 32 bits en formato de red (big-endian)
uint32_t float_to_network(float value) {
    uint32_t as_int;
    memcpy(&as_int, &value, sizeof(float));
    return htonl(as_int);
}

// Firma los datos usando SHA-256 + RSA
unsigned char* firmar_sha256(const char* mensaje, size_t len, size_t& firma_len) {
    // Abre archivo de clave privada
    FILE* fp = fopen("private_key.pem", "r");
    if (!fp) throw std::runtime_error("No se pudo abrir private_key.pem");
    
    // Lee la clave privada
    EVP_PKEY* pkey = PEM_read_PrivateKey(fp, nullptr, nullptr, nullptr);
    fclose(fp);
    if (!pkey) throw std::runtime_error("Error leyendo la clave privada");

    // Crea contexto de firma
    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    if (!mdctx) {
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error creando el contexto de firma");
    }

    // Inicializa para firmar con SHA-256
    if (EVP_DigestSignInit(mdctx, nullptr, EVP_sha256(), nullptr, pkey) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error inicializando DigestSign");
    }

    // Procesa el mensaje
    if (EVP_DigestSignUpdate(mdctx, mensaje, len) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error actualizando DigestSign");
    }

    // Obtiene el tamaño necesario para la firma
    if (EVP_DigestSignFinal(mdctx, nullptr, &firma_len) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error obteniendo tamaño de firma");
    }

    // Genera la firma
    unsigned char* firma = new unsigned char[firma_len];
    if (EVP_DigestSignFinal(mdctx, firma, &firma_len) != 1) {
        delete[] firma;
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error generando la firma");
    }

    // Libera recursos
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return firma;
}

// Generadores aleatorios para los sensores
std::random_device rd;
std::mt19937 gen(rd());

// Simula temperatura entre 0.0 y 30.0 °C
float generar_temperatura() {
    std::uniform_real_distribution<float> dis(0.0f, 30.0f);
    return std::round(dis(gen) * 10.0f) / 10.0f;
}

// Simula presión entre 0.7 y 1.3 atm
float generar_presion() {
    std::uniform_real_distribution<float> dis(0.7f, 1.3f);
    return std::round(dis(gen) * 100.0f) / 100.0f;
}

// Simula humedad entre 0 y 100 %
float generar_humedad() {
    std::uniform_real_distribution<float> dis(0.0f, 100.0f);
    return std::round(dis(gen) * 10.0f) / 10.0f;
}

int main() {
    // Inicializa librerías de OpenSSL
    SSL_library_init();
    OpenSSL_add_all_algorithms();

    // Crea contexto TLS cliente
    SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
    if (!ctx) {
        std::cerr << "Error creando contexto SSL." << std::endl;
        return 1;
    }

    // Bucle principal del cliente
    while (true) {
        // Crea socket TCP
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in server{};
        server.sin_family = AF_INET;
        server.sin_port = htons(PORT);
        inet_pton(AF_INET, SERVER_ADDR, &server.sin_addr);

        // Intenta conectar al servidor
        if (connect(sock, (sockaddr*)&server, sizeof(server)) < 0) {
            std::cerr << "Error al conectar con el servidor." << std::endl;
            close(sock);
            std::this_thread::sleep_for(std::chrono::seconds(5));
            continue;
        }

        // Establece conexión TLS
        SSL* ssl = SSL_new(ctx);
        SSL_set_fd(ssl, sock);
        if (SSL_connect(ssl) <= 0) {
            std::cerr << "Error en el handshake TLS." << std::endl;
            SSL_free(ssl);
            close(sock);
            std::this_thread::sleep_for(std::chrono::seconds(5));
            continue;
        }

        // Lee el ID desde archivo local (id.txt)
        std::ifstream f("id.txt");
        int id_val = 1;
        if (f >> id_val) f.close();

        // Construcción del mensaje
        int16_t id = htons(id_val);                              // ID en big-endian
        uint64_t ts = htonll(time(nullptr));                     // Timestamp actual
        uint32_t temp = float_to_network(generar_temperatura()); // Temperatura
        uint32_t pres = float_to_network(generar_presion());     // Presión
        uint32_t hum = float_to_network(generar_humedad());      // Humedad

        // Arreglo con los datos sin firmar
        char buffer[22];
        memcpy(buffer, &id, 2);
        memcpy(buffer + 2, &ts, 8);
        memcpy(buffer + 10, &temp, 4);
        memcpy(buffer + 14, &pres, 4);
        memcpy(buffer + 18, &hum, 4);

        // Firma digital del bloque de datos
        size_t firma_len;
        unsigned char* firma = firmar_sha256(buffer, sizeof(buffer), firma_len);

        // Construye el mensaje final (datos + firma)
        size_t total_len = sizeof(buffer) + firma_len;
        char* mensaje = new char[total_len];
        memcpy(mensaje, buffer, sizeof(buffer));
        memcpy(mensaje + sizeof(buffer), firma, firma_len);

        // Envia mensaje completo cifrado con TLS
        SSL_write(ssl, mensaje, total_len);

        std::cout << "Datos con ID " << id_val << " enviados con firma RSA" << std::endl;

        // Guarda el siguiente ID en archivo
        std::ofstream out("id.txt"); out << id_val + 1; out.close();

        // Libera memoria
        delete[] mensaje;
        delete[] firma;

        // Cierra conexión TLS y socket
        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(sock);

        // Espera 5 segundos antes de volver a enviar
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    // Libera contexto SSL
    SSL_CTX_free(ctx);
    return 0;
}
